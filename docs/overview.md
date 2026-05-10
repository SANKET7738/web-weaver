# Overview

## Three subsystems

```
   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │                  │    │                  │    │                  │
   │  Task generator  │───▶│     Harness      │───▶│      Grader      │
   │                  │    │                  │    │                  │
   └──────────────────┘    └──────────────────┘    └──────────────────┘
            │                       │                       │
   produces harbor task    produces captured agent  produces per-grader
   directory               screenshots + prompt     scores -> reward.json
                           screenshots
```

## Task generator

```
                          ┌──────────────────────┐
                          │     Taxonomies       │
                          │  design_aesthetics   │
                          │  layout_families     │
                          │  page_sets           │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │   Concept sampler    │
                          └──────────┬───────────┘
                                     │
                                     ▼
                              Concept JSON
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │ Blueprint generator  │
                          └──────────┬───────────┘
                                     │
                                     ▼
                            SiteBlueprint JSON
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │ Design-plan generator│
                          └──────────┬───────────┘
                                     │
                                     ▼
                            DesignPlan JSON
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  Site-gen container  │
                          │     Claude Code      │
                          └──────────┬───────────┘
                                     │
                  ┌──────────────────┼──────────────────┐
                  │                  │                  │
                  ▼                  ▼                  ▼
          ┌────────────────┐ ┌─────────────┐  ┌─────────────────┐
          │ Reference site │ │ Screenshots │  │ Screen          │
          │  HTML/CSS/SVG  │ │ tall+slices │  │ recordings      │
          └────────┬───────┘ └──────┬──────┘  └────────┬────────┘
                   │                │                  │
                   └────────────────┼──────────────────┘
                                    │
                                    ▼
                          ┌──────────────────────┐
                          │   Harbor task dir    │
                          └──────────────────────┘
```

### Sample outputs per block

#### Concept sampler → `Assets/Concepts/<id>.json`

```json
{
  "id": "ww-00021",
  "version": "0.1",
  "site_domain": "gaming_entertainment",
  "site_subdomain": "board game cafe",
  "design_aesthetic": "friendly_consumer_app",
  "layout_family": "classic_landing",
  "page_set": ["home", "games", "trailer", "community", "buy"],
  "difficulty": "hard",
  "seed": 88463792,
  "sample_index": 10,
  "source": "web-weaver.concept_sampler"
}
```

#### Blueprint generator → `Assets/Blueprints/<id>.json`

Top-level Pydantic model only; nested types (`PageBlueprint`,
`SectionBlueprint`, `CTA`, `AssetIdea`, etc.) elided.

```python
class SiteBlueprint(BaseModel):
    id: str
    version: str = "0.1"
    concept_id: str
    identity: SiteIdentity
    pages: list[PageBlueprint] = Field(min_length=5)
    constraints: BlueprintConstraints
    source: str = "web-weaver.blueprint_generator"
```

#### Design-plan generator → `Assets/DesignPlans/<id>.json`

Top-level Pydantic model only; nested types (`PageDesignPlan`,
`SectionDesignPlan`, `ColorToken`, `TypographyPlan`) elided.

```python
class DesignPlan(BaseModel):
    id: str
    version: str = "0.1"
    concept_id: str
    blueprint_id: str
    color_palette: list[ColorToken] = Field(min_length=4, max_length=8)
    typography: TypographyPlan
    pages: list[PageDesignPlan] = Field(min_length=5)
    source: str = "web-weaver.layout_engine"
```

#### Site-gen container → `Runs/SiteGeneration/<id>/attempt-NNN/`

```
output/reference_site/
  index.html  page_02.html ... page_NN.html
  styles.css  script.js
  assets/<svg files>

validation/
  screenshots/<slug>/<slug>_full.png
  screenshots/<slug>/<slug>_001.png ... <slug>_NNN.png
  screenrecordings/<slug>.mp4

harbor/
  instruction.md  task.toml
  environment/Dockerfile
  environment/prompt/screenshots/page_NN.png + _full.png + _NNN.png
  environment/solution_assets/screenshots/<slug>/...
  environment/solution_assets/screenrecordings/<slug>.mp4
  environment/grader/run.py
  solution/solve.sh  solution/site/...
  tests/test.sh
```

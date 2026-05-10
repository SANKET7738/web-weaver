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

The task generator is structured as a virtual web design studio. A randomized
Concept sampler plays the *client* and writes the brief; three persona stages
then hand off increasingly concrete artifacts down a single pipeline. The same
persona analogies appear verbatim in the system prompts used at each stage.

```
┌─ CONCEPT SAMPLER ───────────────────────────────────────── sampler.py ─┐
│                                                                        │
│  Seeded mix of taxonomies → TaskConcept                                │
│                                                                        │
│  Domain      site_domain · subdomain                                   │
│  Style       design_aesthetic · layout_family                          │
│  Pages       page_set (5+ slugs)                                       │
│  Difficulty  easy | medium | hard                                      │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  →  TaskConcept    Assets/Concepts/<id>.json                           │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │   "client brief"
                                    ▼
┌─ BRAND DESIGNER ────────────────────────────── blueprint_generator.py ─┐
│                                                                        │
│  "Lead brand designer preparing the brief for the design team."        │
│                                                                        │
│  Decides storytelling & content only — no visuals, no hex, no CSS      │
│                                                                        │
│  Identity    name · tagline · voice · target audience                  │
│  Pages       title · role · goal · meta                                │
│  Sections    type · intent · headline · body · items · CTAs            │
│  Assets      programmatic SVG ideas, gated by difficulty               │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  →  SiteBlueprint    Assets/Blueprints/<id>.json                       │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ UI DESIGNER ────────────────────────── layout_engine.py · two passes ─┐
│                                                                        │
│  "Senior UI/UX designer & visual design director."                     │
│                                                                        │
│  Pass 1 · Shared design system                                         │
│    Palette    4–8 named tokens with usage role                         │
│               (e.g. "Crown Ivory" #F5F0E8)                             │
│    Typography heading / body / accent + treatments                     │
│                                                                        │
│  Pass 2 · Per page                                                     │
│    Page       rhythm · hierarchy · *signature moment* ·                │
│               density · responsive                                     │
│    Section    alignment · grid · scale · color tokens ·                │
│               asset placement                                          │
│                                                                        │
│  Boundary: no HTML/CSS/SVG, no ids — design intent only.               │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  →  DesignPlan    Assets/DesignPlans/<id>.json                         │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ FRONTEND DEVELOPER ───────── site_generator/ · Claude Code in Docker ─┐
│                                                                        │
│  "Implementation engineer building the reference site verbatim."       │
│                                                                        │
│  Reads      concept + blueprint + design_plan                          │
│  Builds     static HTML/CSS, vanilla JS, inline SVG                    │
│  Wires      data-page-slug, section[id][data-type]                     │
│  Captures   sanity · Playwright · shots · recordings                   │
│                                                                        │
│  No React/Tailwind/external images/backend.                            │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  →  Runs/SiteGeneration/<id>/attempt-NNN/   →   Harbor task dir        │
└────────────────────────────────────────────────────────────────────────┘
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

## Harbor task surface

What the assembled harbor task exposes at solve time — what the agent sees,
what the container has installed, and what the grader can read after the
agent finishes. The container splits cleanly into an agent-readable surface
(`/app/...`) and a root-only locked surface (`/opt/...`).

```
┌─ HARBOR TASK CONTAINER ───────── node:22-slim · playwright + chromium ─┐
│                                                                        │
│  AGENT SURFACE     user: agent                                         │
│                                                                        │
│  /app/prompt/         (read-only — the only inputs agent sees)         │
│    screenshots/       page_NN.png · page_NN_full.png ·                 │
│                       page_NN_NNN.png    (1440x1000 slices)            │
│    screenrecordings/  page_NN.mp4        (1440x1000 @ 25fps)           │
│                                                                        │
│  /app/site/           (writable — agent must produce HTML here)        │
│    index.html · page_NN.html · CSS / vanilla JS / inline SVG           │
│                                                                        │
│  instruction.md       the prompt: replicate every page from the        │
│                       screenshots and recordings                       │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  LOCKED SURFACE    user: root, mode 700 (invisible to agent)           │
│                                                                        │
│  /opt/solution/   ground-truth screenshots + screenrecordings          │
│                   the grader can compare against                       │
│  /opt/grader/     grader/run.py — invoked by tests/test.sh             │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  RULES IN instruction.md                                               │
│    • HTML/CSS + vanilla JS only · no build step                        │
│    • No React/Vue/Tailwind/Bootstrap or component libraries            │
│    • No animation libs (GSAP, Anime.js, Framer, Lottie, AOS …)         │
│    • Inline / local SVG only — no external images or remote media      │
│    • No servers, no backend                                            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ GRADER ─────────────────────────────── tests/test.sh → grader/run.py ─┐
│                                                                        │
│  Runs as root after the agent finishes.                                │
│                                                                        │
│  Reads      /app/site         agent's output                           │
│             /app/prompt       same files the agent saw                 │
│             /opt/solution     ground-truth (root-only)                 │
│                                                                        │
│  Captures   /logs/verifier/agent_screenshots/                          │
│             Playwright @ 1440x1000, full-page PNG/page                 │
│                                                                        │
│  Writes     /logs/verifier/reward.json                                 │
│             /logs/verifier/reward.txt   (Harbor's score)               │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

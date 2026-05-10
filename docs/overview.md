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
                                       Blueprint JSON
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │ Design-plan generator│
                                  └──────────┬───────────┘
                                             │
                                             ▼
                                       Design plan JSON
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

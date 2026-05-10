# Valid Harbor tasks

This file lists every task under `Runs/SiteGeneration/` and whether
it can be run with `harbor run`. A task is **runnable** if its
`harbor/` subdirectory has the four required pieces:

- `task.toml` and `instruction.md` (Harbor task definition)
- `tests/test.sh` (verifier entry point)
- `environment/grader/run.py` (placeholder grader)
- `environment/prompt/screenshots/` (reference page screenshots)

**Animation grading (✅)** requires both reference recordings under
`environment/prompt/screenrecordings/` *and* a verifier wired with
`--recordings-out`. Tasks with recordings but the older `test.sh`
are marked **(rec)** — they can be retro-fitted by re-running
`render_harbor_test_script()` against their `tests/test.sh`.

**Total tasks:** 22  ·  **Runnable:** 18  ·  **Animation-ready:** 3  ·  **Recordings-only:** 4

## How to run

Pick a task ID below, then:

```bash
export ANTHROPIC_API_KEY=$(grep -E '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)
harbor run \
  -p Runs/SiteGeneration/<task_id>/<attempt>/harbor \
  -a claude-code \
  -m claude-opus-4-7
```

The `harbor path` column gives the exact `-p` argument.

## Runnable tasks

| task | brand | subdomain · aesthetic · layout | difficulty | pages | mp4s | anim? | harbor path |
|---|---|---|---|---|---|---|---|
| `ww-00008` | RevvLot | used car marketplace · retro_90s_web · dashboard_product | hard | 5 | 0 | — | `Runs/SiteGeneration/ww-00008/attempt-006/harbor` |
| `ww-00017` | Sproutly | kids clothing label · friendly_consumer_app · gallery_first | medium | 5 | 5 | ✅ | `Runs/SiteGeneration/ww-00017/attempt-001/harbor` |
| `ww-00020` | Levante | Mediterranean mezze bar · corporate_clean · dashboard_product | medium | 5 | 0 | — | `Runs/SiteGeneration/ww-00020/attempt-004/harbor` |
| `ww-00021` | Rollout | board game cafe · friendly_consumer_app · classic_landing | hard | 5 | 0 | — | `Runs/SiteGeneration/ww-00021/attempt-002/harbor` |
| `ww-00022` | BoltWorks | robotics learning club · festival_poster · card_grid | hard | 5 | 0 | — | `Runs/SiteGeneration/ww-00022/attempt-002/harbor` |
| `ww-00023` | Pixelwave | technology trends publication · y2k_gloss · sidebar_navigation | easy | 5 | 0 | — | `Runs/SiteGeneration/ww-00023/attempt-004/harbor` |
| `ww-00024` | Pinnacle Estates | luxury real estate brokerage · corporate_clean · card_grid | easy | 5 | 0 | — | `Runs/SiteGeneration/ww-00024/attempt-002/harbor` |
| `ww-00025` | NEONRIFT | esports tournament · cyberpunk · card_grid | hard | 5 | 0 | — | `Runs/SiteGeneration/ww-00025/attempt-001/harbor` |
| `ww-00026` | Lumi & Bloom | body care brand · friendly_consumer_app · gallery_first | hard | 5 | 5 | ✅ | `Runs/SiteGeneration/ww-00026/attempt-004/harbor` |
| `ww-00027` | Axiom Public Lab | public space design lab · data_heavy · gallery_first | easy | 5 | 0 | — | `Runs/SiteGeneration/ww-00027/attempt-002/harbor` |
| `ww-00028` | Hearthstone Law | estate planning practice · skeuomorphic_modern · card_grid | medium | 5 | 0 | — | `Runs/SiteGeneration/ww-00028/attempt-001/harbor` |
| `ww-00029` | IronPop Gym | strength training gym · memphis_playful · split_panel | easy | 5 | 0 | — | `Runs/SiteGeneration/ww-00029/attempt-001/harbor` |
| `ww-00030` | Axiom Hotel | boutique business hotel · ai_lab · storytelling_scroll | easy | 5 | 0 | — | `Runs/SiteGeneration/ww-00030/attempt-001/harbor` |
| `ww-00031` | Inkwell Jazz Festival | jazz festival · handmade_illustrated · storytelling_scroll | medium | 5 | 5 | ✅ | `Runs/SiteGeneration/ww-00031/attempt-003/harbor` |
| `ww-00032` | Lava Mouth | small-batch hot sauce brand · memphis_playful · storytelling_scroll | hard | 5 | 5 | (rec) | `Runs/SiteGeneration/ww-00032/attempt-002/harbor` |
| `ww-00033` | Forma Intime | lingerie brand · clinical_health · dashboard_product | medium | 5 | 5 | (rec) | `Runs/SiteGeneration/ww-00033/attempt-001/harbor` |
| `ww-00034` | BRUTALK | language learning platform · brutalist_raw · card_grid | hard | 5 | 5 | (rec) | `Runs/SiteGeneration/ww-00034/attempt-001/harbor` |
| `ww-00035` | Haven & Paw | animal rescue shelter · civic_institutional · classic_landing | easy | 5 | 5 | (rec) | `Runs/SiteGeneration/ww-00035/attempt-001/harbor` |

## Tasks not runnable

| task | reason |
|---|---|
| `ww-00002` | no runnable harbor surface |
| `ww-00003` | no runnable harbor surface |
| `ww-00011` | no runnable harbor surface |
| `ww-00040` | no runnable harbor surface |

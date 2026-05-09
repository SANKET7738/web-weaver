import json
import random
import re
from pathlib import Path
from typing import Any

from web_weaver.models import ConceptIndex, Difficulty, TaskConcept
from web_weaver.taxonomies import load_taxonomies


CONCEPT_ID_PATTERN = re.compile(r"^ww-(\d{5})\.json$")
DIFFICULTIES: tuple[Difficulty, ...] = ("easy", "medium", "hard")


def sample_concepts(n: int, seed: int | None = None) -> ConceptIndex:
    if n < 1:
        raise ValueError("n must be at least 1")

    actual_seed = seed if seed is not None else random.SystemRandom().randint(0, 2**32 - 1)
    rng = random.Random(actual_seed)
    taxonomies = load_taxonomies()

    concepts_dir = Path("Assets") / "Concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    next_id = _next_concept_number(concepts_dir)
    concepts: list[TaskConcept] = []

    for offset in range(n):
        concept_number = next_id + offset
        concept = _sample_one(
            concept_id=f"ww-{concept_number:05d}",
            sample_index=offset + 1,
            seed=actual_seed,
            rng=rng,
            taxonomies=taxonomies,
        )
        concepts.append(concept)
        _write_json(concepts_dir / f"{concept.id}.json", concept.model_dump(mode="json"))

    index = ConceptIndex(
        seed=actual_seed,
        count=len(concepts),
        concept_ids=[concept.id for concept in concepts],
        concept_paths=[str(concepts_dir / f"{concept.id}.json") for concept in concepts],
    )
    _write_json(concepts_dir / "index.json", index.model_dump(mode="json"))
    return index


def _sample_one(
    *,
    concept_id: str,
    sample_index: int,
    seed: int,
    rng: random.Random,
    taxonomies: dict[str, Any],
) -> TaskConcept:
    site_concepts = taxonomies["site_concepts"]
    page_sets = taxonomies["page_sets"]
    design_aesthetics = taxonomies["design_aesthetics"]
    layout_families = taxonomies["layout_families"]

    site_domain = rng.choice(sorted(site_concepts))
    site_subdomain = rng.choice(site_concepts[site_domain])
    page_set = rng.choice(page_sets[site_domain])
    design_aesthetic = rng.choice(sorted(design_aesthetics))
    layout_family = _sample_layout_family(site_domain, layout_families, rng)
    difficulty = rng.choice(DIFFICULTIES)

    return TaskConcept(
        id=concept_id,
        site_domain=site_domain,
        site_subdomain=site_subdomain,
        design_aesthetic=design_aesthetic,
        layout_family=layout_family,
        page_set=page_set,
        difficulty=difficulty,
        seed=seed,
        sample_index=sample_index,
    )


def _sample_layout_family(
    site_domain: str, layout_families: dict[str, Any], rng: random.Random
) -> str:
    layout_keys = sorted(layout_families)
    compatible = [
        key
        for key, value in layout_families.items()
        if site_domain in value.get("best_for", [])
    ]

    if compatible and rng.random() < 0.7:
        return rng.choice(sorted(compatible))

    return rng.choice(layout_keys)


def _next_concept_number(concepts_dir: Path) -> int:
    highest = 0
    for path in concepts_dir.glob("ww-*.json"):
        match = CONCEPT_ID_PATTERN.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")

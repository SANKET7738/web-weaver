import json
from pathlib import Path
from typing import Any


class TaxonomyError(ValueError):
    pass


def load_taxonomies(taxonomy_dir: Path = Path("taxonomies")) -> dict[str, Any]:
    site_concepts = _read_json(taxonomy_dir / "site_concept.json")
    design_aesthetics = _read_json(taxonomy_dir / "design_aesthetics.json")
    layout_families = _read_json(taxonomy_dir / "layout_families.json")
    page_sets = _read_json(taxonomy_dir / "page_sets.json")

    site_domains = set(site_concepts)
    page_set_domains = set(page_sets)
    if site_domains != page_set_domains:
        missing = sorted(site_domains - page_set_domains)
        extra = sorted(page_set_domains - site_domains)
        raise TaxonomyError(
            "site_concept.json and page_sets.json domains must match. "
            f"Missing page sets: {missing}; extra page sets: {extra}"
        )

    for domain, sets in page_sets.items():
        invalid_sets = [page_set for page_set in sets if len(page_set) < 5]
        if invalid_sets:
            raise TaxonomyError(
                f"Domain '{domain}' has page sets with fewer than 5 pages: {invalid_sets}"
            )

    return {
        "site_concepts": site_concepts,
        "design_aesthetics": design_aesthetics,
        "layout_families": layout_families,
        "page_sets": page_sets,
    }


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise TaxonomyError(f"Taxonomy file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

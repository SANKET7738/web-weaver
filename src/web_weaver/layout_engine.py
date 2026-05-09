import json
import re
from pathlib import Path

from web_weaver.blueprint_generator import CONCEPTS_DIR, parse_concept_ids
from web_weaver.llm_utils import AnthropicClient
from web_weaver.models import (
    DesignPlan,
    DesignSystemDraft,
    PageBlueprint,
    PageDesignPlan,
    PageDesignPlanDraft,
    SectionDesignPlan,
    SiteBlueprint,
    TaskConcept,
)
from web_weaver.taxonomies import load_taxonomies


BLUEPRINTS_DIR = Path("Assets") / "Blueprints"
DESIGN_PLANS_DIR = Path("Assets") / "DesignPlans"
DEBUG_DIR = Path("Assets") / "Debug"


class DesignPlanValidationError(ValueError):
    pass


def parse_blueprint_ids(raw_blueprint_ids: str) -> list[str]:
    return parse_concept_ids(raw_blueprint_ids)


def generate_design_plans(
    blueprint_ids: list[str],
    *,
    model: str,
    max_tokens: int = 10000,
    dry_run: bool = False,
    debug: bool = False,
) -> list[DesignPlan]:
    client = AnthropicClient()
    taxonomies = load_taxonomies()
    design_plans: list[DesignPlan] = []

    for blueprint_id in blueprint_ids:
        concept = load_concept(blueprint_id)
        blueprint = load_blueprint(blueprint_id)
        design_plan = generate_design_plan(
            concept=concept,
            blueprint=blueprint,
            taxonomies=taxonomies,
            client=client,
            model=model,
            max_tokens=max_tokens,
            debug=debug,
        )
        validate_design_plan_against_blueprint(design_plan, blueprint, concept)
        design_plans.append(design_plan)

        if not dry_run:
            write_design_plan(design_plan)

    return design_plans


def load_concept(concept_id: str) -> TaskConcept:
    concept_path = CONCEPTS_DIR / f"{concept_id}.json"
    if not concept_path.exists():
        raise FileNotFoundError(f"Concept file not found: {concept_path}")
    return TaskConcept.model_validate_json(concept_path.read_text(encoding="utf-8"))


def load_blueprint(blueprint_id: str) -> SiteBlueprint:
    blueprint_path = BLUEPRINTS_DIR / f"{blueprint_id}.json"
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    return SiteBlueprint.model_validate_json(blueprint_path.read_text(encoding="utf-8"))


def generate_design_plan(
    *,
    concept: TaskConcept,
    blueprint: SiteBlueprint,
    taxonomies: dict,
    client: AnthropicClient,
    model: str,
    max_tokens: int,
    debug: bool = False,
) -> DesignPlan:
    design_system = generate_design_system(
        concept=concept,
        blueprint=blueprint,
        taxonomies=taxonomies,
        client=client,
        model=model,
        max_tokens=max_tokens,
        debug=debug,
    )

    page_drafts = [
        generate_page_design_plan(
            concept=concept,
            blueprint=blueprint,
            page_index=page_index,
            design_system=design_system,
            taxonomies=taxonomies,
            client=client,
            model=model,
            max_tokens=max_tokens,
            debug=debug,
        )
        for page_index in range(len(blueprint.pages))
    ]

    pages: list[PageDesignPlan] = []
    for page_index, page_draft in enumerate(page_drafts):
        blueprint_page = blueprint.pages[page_index]
        sections = [
            SectionDesignPlan(
                id=blueprint_page.sections[section_index].id,
                nl_prompt=section_draft.nl_prompt,
            )
            for section_index, section_draft in enumerate(
                page_draft.section_design_plans
            )
        ]
        pages.append(
            PageDesignPlan(
                slug=blueprint_page.slug,
                page_level_design_instruction=page_draft.page_level_design_instruction,
                section_design_plans=sections,
            )
        )

    return DesignPlan(
        id=blueprint.id,
        concept_id=concept.id,
        blueprint_id=blueprint.id,
        color_palette=design_system.color_palette,
        typography=design_system.typography,
        pages=pages,
    )


def generate_design_system(
    *,
    concept: TaskConcept,
    blueprint: SiteBlueprint,
    taxonomies: dict,
    client: AnthropicClient,
    model: str,
    max_tokens: int,
    debug: bool = False,
) -> DesignSystemDraft:
    prompt = build_design_system_prompt(
        concept=concept,
        blueprint=blueprint,
        design_aesthetic=taxonomies["design_aesthetics"][concept.design_aesthetic],
        layout_family=taxonomies["layout_families"][concept.layout_family],
    )
    result = client.prompt_llm(
        model=model,
        question=prompt,
        response_model=DesignSystemDraft,
        max_tokens=min(max_tokens, 4000),
        temperature=0.7,
        retries=1,
    )
    design_system = result["validated_response"]
    try:
        validate_design_system(design_system)
    except DesignPlanValidationError as error:
        if debug:
            write_debug_artifact(
                blueprint.id,
                "design-system",
                {
                    "error": str(error),
                    "draft": design_system.model_dump(mode="json"),
                },
            )
        raise
    return design_system


def generate_page_design_plan(
    *,
    concept: TaskConcept,
    blueprint: SiteBlueprint,
    page_index: int,
    design_system: DesignSystemDraft,
    taxonomies: dict,
    client: AnthropicClient,
    model: str,
    max_tokens: int,
    debug: bool = False,
) -> PageDesignPlanDraft:
    page = blueprint.pages[page_index]
    expected_section_count = len(page.sections)
    last_error: DesignPlanValidationError | None = None

    for _ in range(3):
        prompt = build_page_design_prompt(
            concept=concept,
            blueprint=blueprint,
            page_index=page_index,
            design_system=design_system,
            design_aesthetic=taxonomies["design_aesthetics"][concept.design_aesthetic],
            layout_family=taxonomies["layout_families"][concept.layout_family],
            previous_error=str(last_error) if last_error else None,
        )
        result = client.prompt_llm(
            model=model,
            question=prompt,
            response_model=PageDesignPlanDraft,
            max_tokens=min(max_tokens, 6000),
            temperature=0.7,
            retries=1,
        )
        page_draft = result["validated_response"]
        try:
            validate_page_design_draft_against_blueprint(page_draft, page)
            return page_draft
        except DesignPlanValidationError as error:
            last_error = error
            if debug:
                write_debug_artifact(
                    blueprint.id,
                    f"page-{page_index + 1}-attempt",
                    {
                        "page_slug": page.slug,
                        "attempt_error": str(error),
                        "draft": page_draft.model_dump(mode="json"),
                    },
                )

    raise DesignPlanValidationError(str(last_error))


def build_design_system_prompt(
    *,
    concept: TaskConcept,
    blueprint: SiteBlueprint,
    design_aesthetic: dict,
    layout_family: dict,
) -> str:
    concept_brief = {
        "site_domain": concept.site_domain,
        "site_subdomain": concept.site_subdomain,
        "design_aesthetic": concept.design_aesthetic,
        "layout_family": concept.layout_family,
        "difficulty": concept.difficulty,
    }
    return f"""
You are the senior UI/UX designer and visual design director in a web design
studio. You receive a brand and content blueprint from the lead brand designer.
Your job is to create the shared visual design system before page-level design.

Do not write HTML, CSS, SVG code, or implementation snippets. Do not output
page slugs, section ids, concept ids, blueprint ids, source metadata, or file
paths. The system adds those programmatically after validation.

Task concept:
{json.dumps(concept_brief, indent=2)}

Design aesthetic guidance:
{json.dumps(design_aesthetic, indent=2)}

Layout family guidance:
{json.dumps(layout_family, indent=2)}

Brand/content blueprint summary:
{json.dumps(compact_blueprint_summary(blueprint), indent=2)}

Required output for this call:
- color_palette: choose 4 to 8 named brand colors with valid hex codes and usage notes.
- typography: choose only freely accessible fonts, preferably from Google Fonts or system web-safe stacks. Good options include Inter, IBM Plex Sans, IBM Plex Serif, IBM Plex Mono, Roboto, Source Sans 3, Source Serif 4, Space Grotesk, Work Sans, Manrope, Lora, Playfair Display, Merriweather, JetBrains Mono, Fira Code, DM Sans, Archivo, Libre Franklin, and Montserrat. Do not choose proprietary/commercial fonts such as Neue Haas Grotesk, Helvetica Neue, Graphik, Avenir, or Circular.
- Make palette and typography decisions concrete enough for all pages to share.

This call only returns the shared DesignSystemDraft. Page design plans are
generated in separate per-page calls, then the pipeline assembles the final
DesignPlan artifact programmatically.

The output must be valid JSON matching the full schema for this call. Use this
shape as an example:

{{
  "color_palette": [
    {{"name": "Brand Ink", "hex": "#111827", "usage": "Primary text and dark surfaces"}},
    {{"name": "Brand Paper", "hex": "#F8F5EF", "usage": "Main background"}},
    {{"name": "Brand Accent", "hex": "#C46A35", "usage": "Buttons and key highlights"}},
    {{"name": "Brand Mist", "hex": "#DCE7E2", "usage": "Soft panels and section backgrounds"}}
  ],
  "typography": {{
    "heading_font": "Space Grotesk",
    "body_font": "Inter",
    "accent_font": "IBM Plex Mono",
    "heading_treatment": "Large expressive headings with tight tracking and clear hierarchy.",
    "body_treatment": "Readable body copy with comfortable line length and generous line height.",
    "accent_treatment": "Small uppercase labels for eyebrows, metadata, and captions."
  }}
}}

Return only the structured JSON response required by the tool schema.
""".strip()


def build_page_design_prompt(
    *,
    concept: TaskConcept,
    blueprint: SiteBlueprint,
    page_index: int,
    design_system: DesignSystemDraft,
    design_aesthetic: dict,
    layout_family: dict,
    previous_error: str | None = None,
) -> str:
    page = blueprint.pages[page_index]
    concept_brief = {
        "site_domain": concept.site_domain,
        "site_subdomain": concept.site_subdomain,
        "design_aesthetic": concept.design_aesthetic,
        "layout_family": concept.layout_family,
        "difficulty": concept.difficulty,
    }
    retry_note = (
        f"\nPrevious invalid output to correct: {previous_error}\n"
        if previous_error
        else ""
    )
    return f"""
You are the senior UI/UX designer and visual design director in a web design
studio. Generate the visual design plan for one page of a synthetic website.

Do not write HTML, CSS, SVG code, or implementation snippets. Do not output
page slugs, section ids, concept ids, blueprint ids, source metadata, or file
paths. The system adds those programmatically after validation.

Task concept:
{json.dumps(concept_brief, indent=2)}

Design aesthetic guidance:
{json.dumps(design_aesthetic, indent=2)}

Layout family guidance:
{json.dumps(layout_family, indent=2)}

Shared design system already chosen:
{design_system.model_dump_json(indent=2)}

Site identity:
{blueprint.identity.model_dump_json(indent=2)}

All site pages, for cross-page rhythm:
{json.dumps([{"slug": p.slug, "title": p.title, "role": p.role, "goal": p.goal} for p in blueprint.pages], indent=2)}

Current page to design, page {page_index + 1} of {len(blueprint.pages)}:
{page.model_dump_json(indent=2)}
{retry_note}
Required output for this call:
- Return exactly one PageDesignPlanDraft object for the current page.
- Do not include the page slug.
- page_level_design_instruction must be a detailed natural-language instruction for the full page layout: section rhythm, color or gradient usage, visual hierarchy, density, responsive behavior, and how this page fits the shared design system.
- section_design_plans must contain exactly {len(page.sections)} items, one for each section in the current page, preserving section order.
- Do not include section ids.
- Each section nl_prompt must be detailed and specific to that section. Use its type, intent, eyebrow, headline, subheadline, body, CTAs, items, and asset ideas.
- Mention asset placement and position when the section has asset ideas.
- Make all page-level and section-level visual decisions here. Do not leave layout, spacing, component styling, or asset placement decisions for the frontend compiler.

This call only returns one PageDesignPlanDraft. The pipeline injects the page
slug and section ids, combines it with the shared DesignSystemDraft, and writes
the final DesignPlan artifact.

The output must be valid JSON matching the full schema for this call. Example
shape:

{{
  "page_level_design_instruction": "Detailed page-level design direction...",
  "section_design_plans": [
    {{"nl_prompt": "Detailed section-level design prompt..."}}
  ]
}}

Return only the structured JSON response required by the tool schema.
""".strip()


def compact_blueprint_summary(blueprint: SiteBlueprint) -> dict:
    return {
        "identity": blueprint.identity.model_dump(mode="json"),
        "pages": [
            {
                "slug": page.slug,
                "title": page.title,
                "role": page.role,
                "goal": page.goal,
                "section_count": len(page.sections),
                "section_types": [section.type for section in page.sections],
            }
            for page in blueprint.pages
        ],
    }


def validate_design_plan_against_blueprint(
    design_plan: DesignPlan,
    blueprint: SiteBlueprint,
    concept: TaskConcept,
) -> None:
    errors: list[str] = []

    if len(design_plan.pages) != len(blueprint.pages):
        errors.append(
            f"expected {len(blueprint.pages)} page plans, got {len(design_plan.pages)}"
        )

    for page_index, page in enumerate(design_plan.pages[: len(blueprint.pages)]):
        blueprint_page = blueprint.pages[page_index]
        if len(page.section_design_plans) != len(blueprint_page.sections):
            errors.append(
                f"page {page_index + 1} expected {len(blueprint_page.sections)} "
                f"section plans, got {len(page.section_design_plans)}"
            )

        try:
            validate_text_instruction(
                page.page_level_design_instruction,
                f"page {page_index + 1} design instruction",
            )
        except DesignPlanValidationError as error:
            errors.append(str(error))

        for section_index, section in enumerate(
            page.section_design_plans[: len(blueprint_page.sections)]
        ):
            blueprint_section = blueprint_page.sections[section_index]
            try:
                validate_text_instruction(
                    section.nl_prompt,
                    f"page {page_index + 1} section {section_index + 1} design prompt",
                )
                validate_asset_placement_coverage(
                    section.nl_prompt,
                    blueprint_section.asset_ideas,
                    f"page {page_index + 1} section {section_index + 1}",
                )
            except DesignPlanValidationError as error:
                errors.append(str(error))

    if errors:
        raise DesignPlanValidationError("; ".join(errors))


def validate_design_system(design_system: DesignSystemDraft) -> None:
    errors: list[str] = []
    color_names = [color.name.lower().strip() for color in design_system.color_palette]
    if len(color_names) != len(set(color_names)):
        errors.append("color palette names must be unique")

    for color in design_system.color_palette:
        if len(color.usage.strip()) < 20:
            errors.append(f"usage for color {color.name} is too short")

    for label, value in [
        ("heading_treatment", design_system.typography.heading_treatment),
        ("body_treatment", design_system.typography.body_treatment),
    ]:
        if len(value.strip()) < 40:
            errors.append(f"{label} is too short")

    proprietary_font_names = [
        "neue haas",
        "helvetica neue",
        "graphik",
        "avenir",
        "circular",
    ]
    selected_fonts = [
        design_system.typography.heading_font,
        design_system.typography.body_font,
        design_system.typography.accent_font or "",
    ]
    for font in selected_fonts:
        lowered_font = font.lower()
        if any(name in lowered_font for name in proprietary_font_names):
            errors.append(f"font must be freely accessible, got {font}")

    if errors:
        raise DesignPlanValidationError("; ".join(errors))


def validate_page_design_draft_against_blueprint(
    page_draft: PageDesignPlanDraft,
    blueprint_page: PageBlueprint,
) -> None:
    errors: list[str] = []

    if len(page_draft.section_design_plans) != len(blueprint_page.sections):
        errors.append(
            f"expected {len(blueprint_page.sections)} section design plans for "
            f"page {blueprint_page.slug}, got {len(page_draft.section_design_plans)}"
        )

    try:
        validate_text_instruction(
            page_draft.page_level_design_instruction,
            f"page {blueprint_page.slug} design instruction",
        )
    except DesignPlanValidationError as error:
        errors.append(str(error))

    for section_index, section_draft in enumerate(
        page_draft.section_design_plans[: len(blueprint_page.sections)]
    ):
        blueprint_section = blueprint_page.sections[section_index]
        label = f"page {blueprint_page.slug} section {section_index + 1}"
        try:
            validate_text_instruction(section_draft.nl_prompt, f"{label} design prompt")
            validate_asset_placement_coverage(
                section_draft.nl_prompt,
                blueprint_section.asset_ideas,
                label,
            )
        except DesignPlanValidationError as error:
            errors.append(str(error))

    if errors:
        raise DesignPlanValidationError("; ".join(errors))


def validate_text_instruction(text: str, label: str) -> None:
    stripped_text = text.strip()
    errors: list[str] = []
    if len(stripped_text) < 120:
        errors.append(f"{label} is too short")

    lowered = stripped_text.lower()
    forbidden_code_patterns = {
        "html tag": r"<\s*/?\s*(div|section|header|main|footer|article|nav)\b",
        "class attribute": r"\bclass\s*=",
        "function declaration": r"\bfunction\s+[a-zA-Z_$][\w$]*\s*\(",
        "const declaration": r"\bconst\s+[a-zA-Z_$][\w$]*\s*=",
        "let declaration": r"\blet\s+[a-zA-Z_$][\w$]*\s*=",
        "var declaration": r"\bvar\s+[a-zA-Z_$][\w$]*\s*=",
        "css media query": r"@media\b",
    }
    found_markers = [
        label
        for label, pattern in forbidden_code_patterns.items()
        if re.search(pattern, lowered)
    ]
    if found_markers:
        errors.append(
            f"{label} must be natural-language design direction, not code "
            f"({', '.join(found_markers)})"
        )

    if errors:
        raise DesignPlanValidationError("; ".join(errors))


def validate_asset_placement_coverage(
    text: str,
    asset_ideas: list,
    label: str,
) -> None:
    if not asset_ideas:
        return

    lowered = text.lower()
    asset_terms = {
        "asset",
        "illustration",
        "icon",
        "logo",
        "pattern",
        "mockup",
        "map",
        "chart",
        "visual",
    }
    placement_terms = {
        "left",
        "right",
        "top",
        "bottom",
        "above",
        "below",
        "beside",
        "behind",
        "background",
        "foreground",
        "center",
        "corner",
        "adjacent",
        "inside",
        "overlap",
    }

    mentions_asset = any(term in lowered for term in asset_terms)
    mentions_placement = any(term in lowered for term in placement_terms)
    if not mentions_asset or not mentions_placement:
        raise DesignPlanValidationError(
            f"{label} has asset ideas but does not describe asset placement"
        )


def write_debug_artifact(blueprint_id: str, label: str, payload: dict) -> Path:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^a-zA-Z0-9_.-]+", "-", label).strip("-")
    existing = sorted(DEBUG_DIR.glob(f"{blueprint_id}-{safe_label}-*.json"))
    debug_path = DEBUG_DIR / f"{blueprint_id}-{safe_label}-{len(existing) + 1:02d}.json"
    with debug_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")
    return debug_path


def write_design_plan(design_plan: DesignPlan) -> Path:
    DESIGN_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    design_plan_path = DESIGN_PLANS_DIR / f"{design_plan.id}.json"
    with design_plan_path.open("w", encoding="utf-8") as file:
        json.dump(design_plan.model_dump(mode="json"), file, indent=2)
        file.write("\n")
    return design_plan_path

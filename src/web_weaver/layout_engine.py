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
    max_tokens: int = 16000,
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
        max_tokens=max_tokens,
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
    last_error: Exception | None = None

    for attempt_index in range(3):
        prompt = build_page_design_prompt(
            concept=concept,
            blueprint=blueprint,
            page_index=page_index,
            design_system=design_system,
            design_aesthetic=taxonomies["design_aesthetics"][concept.design_aesthetic],
            layout_family=taxonomies["layout_families"][concept.layout_family],
            previous_error=str(last_error) if last_error else None,
        )
        try:
            result = client.prompt_llm(
                model=model,
                question=prompt,
                response_model=PageDesignPlanDraft,
                max_tokens=max_tokens,
                temperature=0.7,
                retries=1,
            )
        except ValueError as error:
            last_error = error
            if debug:
                write_debug_artifact(
                    blueprint.id,
                    f"page-{page_index + 1}-attempt-{attempt_index + 1}-schema",
                    {
                        "page_slug": page.slug,
                        "attempt_error": str(error),
                    },
                )
            continue

        page_draft = result["validated_response"]
        try:
            validate_page_design_draft_against_blueprint(page_draft, page)
            return page_draft
        except DesignPlanValidationError as error:
            last_error = error
            if debug:
                write_debug_artifact(
                    blueprint.id,
                    f"page-{page_index + 1}-attempt-{attempt_index + 1}",
                    {
                        "page_slug": page.slug,
                        "attempt_error": str(error),
                        "draft": page_draft.model_dump(mode="json"),
                    },
                )

    raise DesignPlanValidationError(
        f"Failed to generate a valid PageDesignPlanDraft for page "
        f"{page_index + 1} ({page.slug}) after 3 attempts. Last error: {last_error}"
    )


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

Creative direction — read carefully:
- The single most important goal here is to build a system that feels unmistakably like *this* aesthetic for *this* brand — not a neutral, modern-SaaS default. A reviewer should recognize the aesthetic from the palette and typography alone, before ever seeing a layout.
- Lean into the aesthetic's traits, visual_cues, typography hints, and palette_mood at full amplitude. A swiss_modern brief should look severe, grid-driven, and typographically dominant — not "minimalist with a red accent". A maximalist_collage brief should be loud, layered, mixed-scale — not "bright with a few patterns". A heritage_classic brief should feel storied, formal, and ornamental — not "navy and gold added to a startup site". A cyberpunk brief should feel nocturnal and electric, not "dark mode with a neon button".
- Resist the modern-SaaS default (off-white background + single warm accent + Inter / Space Grotesk / IBM Plex Mono trio + neutral grays). Use this stack only when the aesthetic genuinely demands it (e.g., bento_modular, startup_gradient, corporate_clean). For every other aesthetic, both the palette and the font pairing must depart visibly from this template.
- Make the palette_mood dominate. If palette_mood lists "neon, cyan, purple, lime, black", the system needs neon-saturated colors, not muted derivatives. If it lists "cream, black, warm neutral, gold accent", the system should feel editorial, not brand-safe. Saturation, value, temperature, and unusual hues are encouraged whenever the aesthetic supports them.
- Color names must be evocative and brand-specific (e.g., "Crown Ivory", "Nullpoint Signal", "Clearmind Sage"), not generic ("Brand Primary", "Brand Background"). Lazy names produce lazy systems.
- Typography pairings should match the aesthetic's typography hints exactly: heritage / editorial → high-contrast serif + small-caps sans accent; brutalist → heavy display or system mono; memphis / playful → bold geometric or rounded sans + display accent; swiss → neo-grotesque, possibly with a single mono; cinematic → serif display + minimal sans; terminal_hacker → monospace primary. Pick a pairing where each face has a distinct voice — do not default to three near-neutral grotesks by reflex.
- Read the typography hint literally. When the hint says "X accents" or "X font accents", that face is for SMALL ACCENT USE ONLY (eyebrows, badges, stickers, captions, metadata at ≤14px) — it MUST NOT be promoted to the primary heading_font, body_font, or any display-scale role. The primary heading and body fonts must come from the non-accent items in the typography hint, or from the prose-described primary face. Likewise, when the hint lists "system X" or "system fonts", lean on actual system / web-safe stacks (Times New Roman, Georgia, Verdana, Arial, Trebuchet MS, Comic Sans, Courier New) rather than substituting a modern Google grotesque.
- Read the aesthetic holistically — do not collapse it into adjacent aesthetics. retro_90s_web is GeoCities/Netscape/AOL-era amateur web (system fonts, tiled wallpapers, web-safe clashing colors, beveled buttons, animated-GIF energy), NOT cyberpunk/synthwave/arcade-gaming (those belong to cyberpunk and vaporwave). y2k_gloss is chrome-and-bubblegum, not vaporwave. terminal_hacker is monochrome CLI green-on-black, not full neon spectrum. If two aesthetics could plausibly fit, the chosen one anchors the system; do not drift toward the other.
- Stick to the inputs. Every choice you make must be traceable back to the design_aesthetic's traits / visual_cues / typography / palette_mood, the layout_family's structure_cues, or the brand identity. Flair without grounding becomes noise.

Required output for this call:
- color_palette: 4 to 8 named brand colors with valid hex codes and usage notes. The set must reflect the aesthetic's palette_mood; each color's `usage` must explain its specific role and where it appears across the site, not just "background" or "accent".
- typography: choose only freely accessible fonts, preferably from Google Fonts or system web-safe stacks. Good options include Inter, IBM Plex Sans, IBM Plex Serif, IBM Plex Mono, Roboto, Source Sans 3, Source Serif 4, Space Grotesk, Work Sans, Manrope, Lora, Playfair Display, Merriweather, JetBrains Mono, Fira Code, DM Sans, Archivo, Libre Franklin, Montserrat — and for retro / system-flavored aesthetics also Tinos (Times metric clone), Arimo (Arial metric clone), Cousine (Courier New metric clone), Comic Neue (Comic Sans clone), Special Elite (typewriter), VT323 (CRT terminal), Silkscreen (true pixel UI font for ≤12px accents only), and Press Start 2P (8-bit arcade — only for cyberpunk / arcade-flavored aesthetics, never for retro_90s_web). System web-safe stacks (Times New Roman, Georgia, Verdana, Arial, Trebuchet MS, Courier New, Comic Sans MS) are also fair game when the aesthetic calls for them — express them via a stack like `'Times New Roman', Times, serif`. Pick the pairing that fits the aesthetic; do not choose proprietary/commercial fonts such as Neue Haas Grotesk, Helvetica Neue, Graphik, Avenir, or Circular.
- Make palette and typography decisions concrete enough for all pages to share, but expressive enough that the system already feels like the aesthetic in motion.

This call only returns the shared DesignSystemDraft. Page design plans are
generated in separate per-page calls, then the pipeline assembles the final
DesignPlan artifact programmatically.

The output must be valid JSON matching the full schema for this call. The shape
below is illustrative only — it shows one heritage / editorial system to
demonstrate the level of specificity expected. Do NOT copy these names, hex
codes, or fonts unless your aesthetic genuinely matches; your palette and
typography must be derived from the design_aesthetic and brand identity above.

{{
  "color_palette": [
    {{"name": "Crown Ivory", "hex": "#F5F0E8", "usage": "Primary parchment background and card surfaces, evoking heritage warmth across all sections"}},
    {{"name": "Courtside Navy", "hex": "#1B2A4A", "usage": "Primary text, navigation bar, and dark anchoring panels in hero and footer"}},
    {{"name": "Burgundy Crest", "hex": "#7D1D3F", "usage": "Primary CTAs, active states, ornamental dividers, and key highlight moments"}},
    {{"name": "Championship Gold", "hex": "#B8962E", "usage": "Decorative accents, badges, eyebrow labels on dark surfaces, and ornamental rule lines"}}
  ],
  "typography": {{
    "heading_font": "Playfair Display",
    "body_font": "Source Serif 4",
    "accent_font": "Montserrat",
    "heading_treatment": "Elegant high-contrast serif at large display sizes, sentence case, tight tracking on display weights, classical hierarchy with clear weight differentiation between H1, H2, and H3.",
    "body_treatment": "Source Serif 4 at 17–18px with a 1.7 line-height and moderate measure, honoring an editorial register for long-form copy and section descriptions.",
    "accent_treatment": "Montserrat in small caps with wide letter-spacing for eyebrow labels, stat captions, and metadata — a formal sans counterpoint to the serif body."
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
Creative direction — read carefully:
- This page must feel unmistakably like *this* aesthetic for *this* brand. Avoid the modern-SaaS marketing template (split hero with text-left and illustration-right + eyebrow → headline → subheadline → two CTA buttons, three identical card columns, accent color used only on CTAs and eyebrows, alternating off-white sections) unless the aesthetic and layout family genuinely call for it.
- Lean into the aesthetic's visual_cues at full amplitude. If the aesthetic mentions ornamental dividers, treat them as a structural device, not a decorative afterthought. If it mentions overlapping cutouts, stickers, or patterns, OVERLAP them across panels — do not tuck them into corners. If it mentions full-bleed photography or grid horizons, let them DOMINATE the page rather than sit politely beside text. If it mentions hard borders and flat blocks, COMMIT to them at full weight.
- Vary the section skeleton across the page. Not every section should be eyebrow → headline → subheadline → CTA stack. Mix in moves that fit the layout_family's structure_cues — full-bleed type, off-grid pull quotes, type-as-image moments, oversized numerals, asymmetric splits, masthead-style headers, marquee strips, side-tabbed layouts, dense list/index blocks, alternating dense/sparse rhythm, captioned image panels, comparison tables. The same skeleton repeated five times is what makes a page feel templated.
- Each page must contain at least one *signature moment* — a memorable, page-defining visual move that comes from the aesthetic. This could be a typographic stunt (oversized display word, vertical type, headline that bleeds off the grid, dramatic weight contrast), an unconventional composition (diagonal cut, off-axis hero, full-bleed asset crossing several columns), a striking color block (a saturated panel that breaks the section-background alternation), or a distinctive ornamental treatment (a custom rule, a recurring crest / sticker / pattern, layered transparencies, an oversized initial). State clearly in the page-level instruction what the signature moment is, where it lives, and why it belongs to *this* aesthetic.
- Calibrate the signature moment to the aesthetic's energy. A minimalist signature is a bold negative-space gesture or a single unexpected weight contrast; a brutalist signature is unapologetically loud and structural; a heritage signature is ornamental restraint; a maximalist signature is layered density. The move must feel inevitable for *this* aesthetic — never imported from another.
- Resist symmetry by default. Use centered compositions only when the aesthetic and layout structurally demand them (e.g., a heritage_classic CTA close, a swiss_modern terminal block). Otherwise, prefer asymmetry, off-grid alignment, and the structural tension already implied by the design_aesthetic.
- Make color do work. The accent color should not appear *only* on CTA buttons and eyebrow labels. Let it carry oversized typography, ornamental rules, occupy a full-bleed panel, tint photography, or anchor a stat — wherever the aesthetic supports it. Reuse non-accent palette colors expressively too, not just as section backgrounds.
- Stick to the inputs. Every creative move you make must be traceable back to the design_aesthetic's traits / visual_cues / typography / palette_mood, the layout_family's structure_cues, the page's role / goal, the section's type / intent / items / asset_ideas, or the brand identity. No invented motifs that aren't grounded in those inputs. Artistic flair without grounding becomes noise.

Required output for this call:
- Return exactly one PageDesignPlanDraft object for the current page.
- The JSON object MUST include BOTH top-level fields: `page_level_design_instruction` (string) AND `section_design_plans` (array). A response that omits `section_design_plans`, or returns it empty, is invalid and will be rejected — no exceptions, regardless of how detailed the page-level instruction is.
- `section_design_plans` MUST contain exactly {len(page.sections)} items, one for each section in the current page, preserving section order. Each item is an object with a single `nl_prompt` string field.
- Do not include the page slug.
- Do not include section ids.
- page_level_design_instruction must describe the full page in detail: section sequence and how the rhythm varies, color and surface usage across sections, typographic hierarchy and its expressive moves, density / whitespace logic, the page's signature moment (named explicitly), responsive behavior, and how this page fits the shared design system while still being its own composition.
- Each section nl_prompt must be detailed and specific to that section. Use its type, intent, eyebrow, headline, subheadline, body, CTAs, items, and asset ideas. Spell out exact alignment, grid columns, typographic scale and weight, color tokens used, padding / spacing rhythm, and any section-level signature move where one exists.
- Mention asset placement and position when the section has asset ideas (left / right / top / bottom / behind / overlapping / inside / corner / etc.) and explain briefly why that placement reinforces the aesthetic.
- Make all page-level and section-level visual decisions here. Do not leave layout, spacing, component styling, or asset placement decisions for the frontend compiler.

This call only returns one PageDesignPlanDraft. The pipeline injects the page
slug and section ids, combines it with the shared DesignSystemDraft, and writes
the final DesignPlan artifact.

The output must be valid JSON matching the full schema for this call. Shape:

{{
  "page_level_design_instruction": "Page-level direction covering section sequence and rhythm, color and surface usage, typographic hierarchy, the named signature moment, density logic, and responsive behavior — written so the frontend compiler can implement without making further design decisions.",
  "section_design_plans": [
    {{"nl_prompt": "Section-level direction with exact alignment, grid columns, type scale and weight, color tokens used, spacing rhythm, asset placement and reasoning, and any section-specific signature move."}}
  ]
}}

Final reminder before you respond: emit BOTH `page_level_design_instruction`
AND `section_design_plans` in a single JSON object. `section_design_plans` must
contain exactly {len(page.sections)} item(s), in section order. Do not skip it.

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

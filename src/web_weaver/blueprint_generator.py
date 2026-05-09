import json
from pathlib import Path

from web_weaver.llm_utils import AnthropicClient
from web_weaver.models import (
    AssetIdea,
    PageBlueprint,
    SectionBlueprint,
    SiteBlueprint,
    SiteBlueprintDraft,
    SiteIdentity,
    TaskConcept,
)


CONCEPTS_DIR = Path("Assets") / "Concepts"
BLUEPRINTS_DIR = Path("Assets") / "Blueprints"


class BlueprintValidationError(ValueError):
    pass


def parse_concept_ids(raw_concept_ids: str) -> list[str]:
    concept_ids = [
        concept_id.strip()
        for concept_id in raw_concept_ids.split(",")
        if concept_id.strip()
    ]
    if not concept_ids:
        raise ValueError("At least one concept ID is required")
    return concept_ids


def generate_blueprints(
    concept_ids: list[str],
    *,
    model: str,
    max_tokens: int = 128000,
    dry_run: bool = False,
) -> list[SiteBlueprint]:
    client = AnthropicClient()
    blueprints: list[SiteBlueprint] = []

    for concept_id in concept_ids:
        concept = load_concept(concept_id)
        blueprint = generate_blueprint(
            concept=concept,
            client=client,
            model=model,
            max_tokens=max_tokens,
        )
        validate_blueprint_against_concept(blueprint, concept)
        blueprints.append(blueprint)

        if not dry_run:
            write_blueprint(blueprint)

    return blueprints


def load_concept(concept_id: str) -> TaskConcept:
    concept_path = CONCEPTS_DIR / f"{concept_id}.json"
    if not concept_path.exists():
        raise FileNotFoundError(f"Concept file not found: {concept_path}")
    return TaskConcept.model_validate_json(concept_path.read_text(encoding="utf-8"))


def generate_blueprint(
    *,
    concept: TaskConcept,
    client: AnthropicClient,
    model: str,
    max_tokens: int,
) -> SiteBlueprint:
    last_error: Exception | None = None
    for attempt in range(3):
        prompt = build_blueprint_prompt(concept, previous_error=last_error)
        try:
            result = client.prompt_llm(
                model=model,
                question=prompt,
                response_model=SiteBlueprintDraft,
                max_tokens=max_tokens,
                temperature=0.7 if attempt == 0 else 0.4,
                retries=0,
            )
            return normalize_blueprint_draft(result["validated_response"], concept)
        except (BlueprintValidationError, ValueError) as error:
            last_error = error

    raise BlueprintValidationError(f"Blueprint generation failed: {last_error}")


def normalize_blueprint_draft(
    draft: SiteBlueprintDraft,
    concept: TaskConcept,
) -> SiteBlueprint:
    if len(draft.pages) != len(concept.page_set):
        raise BlueprintValidationError(
            f"Draft must contain {len(concept.page_set)} pages, got {len(draft.pages)}"
        )

    pages: list[PageBlueprint] = []
    for page_index, page_draft in enumerate(draft.pages):
        page_slug = concept.page_set[page_index]
        sections: list[SectionBlueprint] = []

        for section_index, section_draft in enumerate(page_draft.sections):
            section_id = f"{page_slug}-section-{section_index + 1}"
            asset_ideas = [
                AssetIdea(
                    id=f"{section_id}-asset-{asset_index + 1}",
                    kind=asset_draft.kind,
                    subject=asset_draft.subject,
                    purpose=asset_draft.purpose,
                    quantity=asset_draft.quantity,
                    used_by=[section_id],
                )
                for asset_index, asset_draft in enumerate(section_draft.asset_ideas)
            ]
            sections.append(
                SectionBlueprint(
                    id=section_id,
                    type=section_draft.type,
                    intent=section_draft.intent,
                    eyebrow=section_draft.eyebrow,
                    headline=section_draft.headline,
                    subheadline=section_draft.subheadline,
                    body=section_draft.body,
                    items=section_draft.items,
                    ctas=section_draft.ctas,
                    asset_ideas=asset_ideas,
                )
            )

        pages.append(
            PageBlueprint(
                slug=page_slug,
                title=page_draft.title,
                role=page_draft.role,
                goal=page_draft.goal,
                meta_description=page_draft.meta_description,
                sections=sections,
            )
        )

    return SiteBlueprint(
        id=concept.id,
        concept_id=concept.id,
        identity=SiteIdentity(
            name=draft.identity.name,
            tagline=draft.identity.tagline,
            one_line_description=draft.identity.one_line_description,
            domain=concept.site_domain,
            subdomain=concept.site_subdomain,
            voice=draft.identity.voice,
            target_audience=draft.identity.target_audience,
        ),
        pages=pages,
    )


def build_blueprint_prompt(
    concept: TaskConcept,
    previous_error: Exception | None = None,
) -> str:
    concept_brief = {
        "site_domain": concept.site_domain,
        "site_subdomain": concept.site_subdomain,
        "design_aesthetic": concept.design_aesthetic,
        "layout_family": concept.layout_family,
        "page_set": concept.page_set,
        "difficulty": concept.difficulty,
    }
    concept_json = json.dumps(concept_brief, indent=2)
    retry_note = (
        "\nPrevious attempt was invalid. Fix this exact issue and return a complete "
        f"top-level object with both identity and pages: {previous_error}\n"
        if previous_error
        else ""
    )
    return f"""
You are the lead brand designer in a web design studio that creates custom
websites for clients. The client has given you a high-level request, and your
job is to understand their domain, subdomain, audience, and business context
deeply enough to turn the request into a storytelling plan for the website.

Think like a senior design manager preparing the brief for your design team.
The client has trusted you to define the site identity, invent a strong brand
name, write a memorable tagline, clarify the target audience for maximum
impact, and decide what content belongs on each page. Your output should read
like the strategic content blueprint that a brand designer, UI designer, and
frontend team can use as their source of truth.

Your job is not to design the interface yet. Your job is to decide the story
the website should tell: what the visitor learns first, what each page is
responsible for, what sections appear on each page, what copy and content each
section needs, what CTAs guide the visitor, and what programmatic SVG asset
ideas would help the design team express the story.

Use the design_aesthetic as creative brand direction. It should influence the
voice, naming, content mood, section themes, and asset ideas. For example, a
retro aesthetic should lead to different language and storytelling than a
clinical, luxury, brutalist, or glassmorphism aesthetic.

Use the layout_family as a high-level storytelling structure. It should
influence the kinds of sections and content groupings you choose. For example,
a dashboard/product layout should include product modules, metrics, and mockup
ideas, while an editorial grid should include richer stories, features,
captions, interviews, or article-like sections. Do not turn layout_family into
pixel layout, CSS, spacing, grid coordinates, or visual implementation.

Important boundaries:
- Generate content, page structure, section content, CTAs, and SVG asset ideas.
- Do not generate visual design implementation.
- Do not specify hex colors, fonts, CSS, spacing, grid coordinates, or image file paths.
- Do not request photos, raster images, external assets, or crawled website assets.
- Any asset ideas must be simple assets that can be generated programmatically as SVG.
- Keep asset usage minimal. Do not add decorative assets unless they help the page story.

Task concept:
{concept_json}
{retry_note}

Required output rules:
- The top-level JSON must contain exactly these required fields: identity and pages.
- pages is required and must be an array. Never return identity by itself.
- Generate exactly one page for each page in this page_set, preserving order:
  {concept.page_set}
- Do not output blueprint ids, concept ids, domain, subdomain, page slugs,
  section ids, asset ids, constraints, or source metadata. The system adds those
  programmatically after validating your draft.
- Every page must have at least one section.
- Every section must have a clear intent and headline.
- Use realistic domain-specific content for the site subdomain.
- CTA target_page values must be null or one of the page slugs in the page_set.
- Asset ideas must use only these kinds: logo, icon, illustration, pattern, mockup, map, chart.
- Asset ideas should be concepts for later SVG generation, not actual SVG code.
- If difficulty is easy, do not include asset ideas.
- If difficulty is medium, include at most 1 simple asset idea per page.
- If difficulty is hard, include at most 2 asset ideas per page.

Difficulty guidance:
- easy: 3 sections per page, simple content, no asset ideas.
- medium: 4 sections per page, richer item lists and at most 1 simple SVG asset idea per page.
- hard: 5 sections per page, richer content such as stats, timelines, comparisons, galleries, or article lists.
  Hard pages can include at most 2 SVG asset ideas per page.

Create a complete blueprint that can later be handed to a UI designer and frontend
compiler.

The output must be valid JSON matching the required schema. Use this shape as
an example of the expected structure:

{{
  "identity": {{
    "name": "Example Brand",
    "tagline": "A short memorable line",
    "one_line_description": "One sentence describing the website and its offer.",
    "voice": ["clear", "confident", "specific"],
    "target_audience": "A precise description of the intended audience."
  }},
  "pages": [
    {{
      "title": "Page Title",
      "role": "landing",
      "goal": "What this page should accomplish for the visitor.",
      "meta_description": "Short page summary.",
      "sections": [
        {{
          "type": "hero",
          "intent": "Why this section exists.",
          "eyebrow": "Optional small label",
          "headline": "Main section message",
          "subheadline": "Short supporting line.",
          "body": null,
          "items": [],
          "ctas": [
            {{"label": "Primary CTA", "target_page": "{concept.page_set[-1]}"}}
          ],
          "asset_ideas": []
        }}
      ]
    }},
    {{
      "title": "Second Page Title",
      "role": "overview",
      "goal": "What the second page should accomplish.",
      "meta_description": "Short page summary.",
      "sections": [
        {{
          "type": "page_header",
          "intent": "Introduce this page.",
          "eyebrow": "Page label",
          "headline": "Second page headline",
          "subheadline": "Short supporting line.",
          "body": null,
          "items": [],
          "ctas": [],
          "asset_ideas": []
        }}
      ]
    }}
  ]
}}

Return only the structured JSON response required by the tool schema.
""".strip()


def validate_blueprint_against_concept(
    blueprint: SiteBlueprint,
    concept: TaskConcept,
) -> None:
    errors: list[str] = []

    if blueprint.id != concept.id:
        errors.append(f"blueprint.id must equal {concept.id}, got {blueprint.id}")
    if blueprint.concept_id != concept.id:
        errors.append(
            f"blueprint.concept_id must equal {concept.id}, got {blueprint.concept_id}"
        )
    if blueprint.identity.domain != concept.site_domain:
        errors.append(
            "identity.domain must equal "
            f"{concept.site_domain}, got {blueprint.identity.domain}"
        )
    if blueprint.identity.subdomain != concept.site_subdomain:
        errors.append(
            "identity.subdomain must equal "
            f"{concept.site_subdomain}, got {blueprint.identity.subdomain}"
        )

    page_slugs = [page.slug for page in blueprint.pages]
    if page_slugs != concept.page_set:
        errors.append(f"page slugs must equal {concept.page_set}, got {page_slugs}")

    page_slug_set = set(page_slugs)
    section_ids = {
        section.id for page in blueprint.pages for section in page.sections
    }

    for page in blueprint.pages:
        asset_count = sum(len(section.asset_ideas) for section in page.sections)
        if concept.difficulty == "easy" and asset_count:
            errors.append(f"easy blueprint page {page.slug} must not include asset ideas")
        if concept.difficulty == "medium" and asset_count > 1:
            errors.append(
                f"medium blueprint page {page.slug} has {asset_count} asset ideas; max is 1"
            )
        if concept.difficulty == "hard" and asset_count > 2:
            errors.append(
                f"hard blueprint page {page.slug} has {asset_count} asset ideas; max is 2"
            )

        for section in page.sections:
            if not section.headline.strip():
                errors.append(f"section {section.id} must have a non-empty headline")
            for cta in section.ctas:
                if cta.target_page is not None and cta.target_page not in page_slug_set:
                    errors.append(
                        f"CTA target_page {cta.target_page} in section {section.id} "
                        f"is not in page set {page_slugs}"
                    )
            for asset_idea in section.asset_ideas:
                for used_by in asset_idea.used_by:
                    if used_by not in section_ids:
                        errors.append(
                            f"asset {asset_idea.id} used_by references unknown "
                            f"section {used_by}"
                        )

    if blueprint.constraints.external_assets_allowed:
        errors.append("external_assets_allowed must be false")
    if blueprint.constraints.asset_policy != "programmatic_svg_only":
        errors.append("asset_policy must be programmatic_svg_only")

    if errors:
        raise BlueprintValidationError("; ".join(errors))


def write_blueprint(blueprint: SiteBlueprint) -> Path:
    BLUEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
    blueprint_path = BLUEPRINTS_DIR / f"{blueprint.id}.json"
    with blueprint_path.open("w", encoding="utf-8") as file:
        json.dump(blueprint.model_dump(mode="json"), file, indent=2)
        file.write("\n")
    return blueprint_path

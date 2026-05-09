from typing import Literal

from pydantic import BaseModel, Field


AssetKind = Literal[
    "logo",
    "icon",
    "illustration",
    "pattern",
    "mockup",
    "map",
    "chart",
]

PageRole = Literal[
    "landing",
    "overview",
    "conversion",
    "detail",
    "listing",
    "editorial",
    "support",
    "contact",
]

SectionType = Literal[
    "hero",
    "page_header",
    "feature_grid",
    "item_grid",
    "story_block",
    "stats",
    "testimonial",
    "cta",
    "faq",
    "contact_block",
    "gallery",
    "pricing",
    "timeline",
    "comparison",
    "map_block",
    "article_list",
]


class SiteIdentity(BaseModel):
    name: str = Field(description="Generated brand, product, or website name.")
    tagline: str = Field(description="Short memorable tagline.")
    one_line_description: str = Field(
        description="One sentence explaining what the website is about."
    )
    domain: str
    subdomain: str
    voice: list[str] = Field(
        description="Tone words for the site content, e.g. calm, technical, playful."
    )
    target_audience: str = Field(description="Primary audience for the website.")


class SiteIdentityDraft(BaseModel):
    name: str = Field(description="Generated brand, product, or website name.")
    tagline: str = Field(description="Short memorable tagline.")
    one_line_description: str = Field(
        description="One sentence explaining what the website is about."
    )
    voice: list[str] = Field(
        description="Tone words for the site content, e.g. calm, technical, playful."
    )
    target_audience: str = Field(description="Primary audience for the website.")


class CTA(BaseModel):
    label: str
    target_page: str | None = None


class ContentItem(BaseModel):
    title: str
    description: str
    metadata: dict[str, str] = Field(default_factory=dict)


class AssetIdea(BaseModel):
    id: str
    kind: AssetKind
    subject: str = Field(description="Conceptual subject of the SVG asset to generate.")
    purpose: str = Field(description="Why this asset is needed in the website.")
    quantity: int = Field(default=1, ge=1)
    used_by: list[str] = Field(
        default_factory=list,
        description="Section IDs that use this asset.",
    )


class AssetIdeaDraft(BaseModel):
    kind: AssetKind
    subject: str = Field(description="Conceptual subject of the SVG asset to generate.")
    purpose: str = Field(description="Why this asset is needed in the website.")
    quantity: int = Field(default=1, ge=1)


class SectionBlueprint(BaseModel):
    id: str
    type: SectionType
    intent: str = Field(description="Why this section exists.")
    eyebrow: str | None = Field(
        default=None,
        description="Small label above the headline, e.g. Features or Our Method.",
    )
    headline: str
    subheadline: str | None = Field(
        default=None,
        description="Short supporting line under the headline.",
    )
    body: str | None = Field(
        default=None,
        description="Longer explanatory text for the section.",
    )
    items: list[ContentItem] = Field(default_factory=list)
    ctas: list[CTA] = Field(default_factory=list)
    asset_ideas: list[AssetIdea] = Field(default_factory=list)


class SectionBlueprintDraft(BaseModel):
    type: SectionType
    intent: str = Field(description="Why this section exists.")
    eyebrow: str | None = Field(
        default=None,
        description="Small label above the headline, e.g. Features or Our Method.",
    )
    headline: str
    subheadline: str | None = Field(
        default=None,
        description="Short supporting line under the headline.",
    )
    body: str | None = Field(
        default=None,
        description="Longer explanatory text for the section.",
    )
    items: list[ContentItem] = Field(default_factory=list)
    ctas: list[CTA] = Field(default_factory=list)
    asset_ideas: list[AssetIdeaDraft] = Field(default_factory=list)


class PageBlueprint(BaseModel):
    slug: str
    title: str
    role: PageRole
    goal: str
    meta_description: str
    sections: list[SectionBlueprint] = Field(min_length=1)


class PageBlueprintDraft(BaseModel):
    title: str
    role: PageRole
    goal: str
    meta_description: str
    sections: list[SectionBlueprintDraft] = Field(min_length=1)


class BlueprintConstraints(BaseModel):
    min_pages: int = Field(default=5, ge=5)
    functionality_required: bool = False
    external_assets_allowed: bool = False
    asset_policy: Literal["programmatic_svg_only"] = "programmatic_svg_only"


class SiteBlueprint(BaseModel):
    id: str
    version: str = "0.1"
    concept_id: str
    identity: SiteIdentity
    pages: list[PageBlueprint] = Field(min_length=5)
    constraints: BlueprintConstraints = Field(default_factory=BlueprintConstraints)
    source: str = "web-weaver.blueprint_generator"


class SiteBlueprintDraft(BaseModel):
    identity: SiteIdentityDraft
    pages: list[PageBlueprintDraft] = Field(min_length=5)

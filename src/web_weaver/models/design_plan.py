from pydantic import BaseModel, Field


class ColorToken(BaseModel):
    name: str
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    usage: str


class TypographyPlan(BaseModel):
    heading_font: str
    body_font: str
    accent_font: str | None = None
    heading_treatment: str
    body_treatment: str
    accent_treatment: str | None = None


class SectionDesignPlanDraft(BaseModel):
    nl_prompt: str


class SectionDesignPlan(BaseModel):
    id: str
    nl_prompt: str


class PageDesignPlanDraft(BaseModel):
    page_level_design_instruction: str
    section_design_plans: list[SectionDesignPlanDraft] = Field(min_length=1)


class PageDesignPlan(BaseModel):
    slug: str
    page_level_design_instruction: str
    section_design_plans: list[SectionDesignPlan] = Field(min_length=1)


class DesignSystemDraft(BaseModel):
    color_palette: list[ColorToken] = Field(min_length=4, max_length=8)
    typography: TypographyPlan


class DesignPlanDraft(BaseModel):
    color_palette: list[ColorToken] = Field(min_length=4, max_length=8)
    typography: TypographyPlan
    pages: list[PageDesignPlanDraft] = Field(min_length=5)


class DesignPlan(BaseModel):
    id: str
    version: str = "0.1"
    concept_id: str
    blueprint_id: str
    color_palette: list[ColorToken] = Field(min_length=4, max_length=8)
    typography: TypographyPlan
    pages: list[PageDesignPlan] = Field(min_length=5)
    source: str = "web-weaver.layout_engine"

from typing import Literal

from pydantic import BaseModel, Field


Difficulty = Literal["easy", "medium", "hard"]


class TaskConcept(BaseModel):
    id: str = Field(description="Stable generated concept ID.")
    version: str = Field(default="0.1")
    site_domain: str
    site_subdomain: str
    design_aesthetic: str
    layout_family: str
    page_set: list[str] = Field(min_length=5)
    difficulty: Difficulty
    seed: int
    sample_index: int = Field(ge=1)
    source: str = Field(default="web-weaver.concept_sampler")


class ConceptIndex(BaseModel):
    version: str = Field(default="0.1")
    seed: int
    count: int = Field(ge=0)
    concept_ids: list[str]
    concept_paths: list[str]

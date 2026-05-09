import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from web_weaver.site_generator.build_env import (
    DEFAULT_PORT,
    default_image_tag,
    resolve_task_artifacts,
)


RUNS_DIR = Path("Runs")
SITE_GENERATION_RUNS_DIR = RUNS_DIR / "SiteGeneration"

AttemptStatus = Literal[
    "created",
    "running",
    "completed",
    "timeout",
    "failed",
    "sanity_passed",
    "sanity_failed",
    "accepted",
    "rejected",
]


def current_timestamp() -> str:
    return datetime.now(UTC).isoformat()


class SiteGenerationAttemptMetadata(BaseModel):
    task_id: str
    attempt_id: str
    status: AttemptStatus = "created"
    agent: str = "claude-code"
    image_tag: str
    container_name: str | None = None
    container_id: str | None = None
    container_port: int = DEFAULT_PORT
    host_port: int | None = None
    timeout_seconds: int = 1800
    created_at: str = Field(default_factory=current_timestamp)
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None
    agent_exit_code: int | None = None
    sanity_valid: bool | None = None
    harbor_candidate: bool = False
    input_path: str = "input"
    output_path: str = "output"
    logs_path: str = "logs"
    validation_path: str = "validation"
    harbor_path: str = "harbor"


@dataclass(frozen=True)
class SiteGenerationAttempt:
    task_id: str
    attempt_id: str
    path: Path

    @property
    def input_dir(self) -> Path:
        return self.path / "input"

    @property
    def output_dir(self) -> Path:
        return self.path / "output"

    @property
    def reference_site_dir(self) -> Path:
        return self.output_dir / "reference_site"

    @property
    def logs_dir(self) -> Path:
        return self.path / "logs"

    @property
    def validation_dir(self) -> Path:
        return self.path / "validation"

    @property
    def screenshots_dir(self) -> Path:
        return self.validation_dir / "screenshots"

    @property
    def harbor_dir(self) -> Path:
        return self.path / "harbor"

    @property
    def metadata_path(self) -> Path:
        return self.path / "metadata.json"

def next_attempt_id(task_id: str) -> str:
    task_runs_dir = SITE_GENERATION_RUNS_DIR / task_id
    max_attempt_number = 0
    if task_runs_dir.exists():
        for attempt_dir in task_runs_dir.glob("attempt-*"):
            suffix = attempt_dir.name.removeprefix("attempt-")
            if suffix.isdigit():
                max_attempt_number = max(max_attempt_number, int(suffix))
    return f"attempt-{max_attempt_number + 1:03d}"


def create_attempt(
    task_id: str,
    *,
    image_tag: str | None = None,
    timeout_seconds: int = 1800,
) -> SiteGenerationAttempt:
    attempt_id = next_attempt_id(task_id)
    attempt = SiteGenerationAttempt(
        task_id=task_id,
        attempt_id=attempt_id,
        path=SITE_GENERATION_RUNS_DIR / task_id / attempt_id,
    )
    create_attempt_dirs(attempt)
    snapshot_inputs(attempt)

    metadata = SiteGenerationAttemptMetadata(
        task_id=task_id,
        attempt_id=attempt_id,
        image_tag=image_tag or default_image_tag(task_id),
        timeout_seconds=timeout_seconds,
    )
    write_metadata(attempt, metadata)
    return attempt


def create_attempt_dirs(attempt: SiteGenerationAttempt) -> None:
    for directory in [
        attempt.input_dir,
        attempt.reference_site_dir,
        attempt.logs_dir,
        attempt.screenshots_dir,
        attempt.harbor_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=False)


def snapshot_inputs(attempt: SiteGenerationAttempt) -> None:
    artifact_paths = resolve_task_artifacts(attempt.task_id)
    shutil.copyfile(artifact_paths["concept"], attempt.input_dir / "concept.json")
    shutil.copyfile(artifact_paths["blueprint"], attempt.input_dir / "blueprint.json")
    shutil.copyfile(
        artifact_paths["design_plan"],
        attempt.input_dir / "design_plan.json",
    )


def load_metadata(
    attempt: SiteGenerationAttempt,
) -> SiteGenerationAttemptMetadata:
    return SiteGenerationAttemptMetadata.model_validate_json(
        attempt.metadata_path.read_text(encoding="utf-8")
    )


def write_metadata(
    attempt: SiteGenerationAttempt,
    metadata: SiteGenerationAttemptMetadata,
) -> None:
    attempt.metadata_path.write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def update_metadata(
    attempt: SiteGenerationAttempt,
    **updates,
) -> SiteGenerationAttemptMetadata:
    metadata = load_metadata(attempt)
    updated_metadata = metadata.model_copy(update=updates)
    write_metadata(attempt, updated_metadata)
    return updated_metadata

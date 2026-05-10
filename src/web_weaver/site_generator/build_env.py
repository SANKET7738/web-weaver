import re
import shutil
import tempfile
from pathlib import Path

from web_weaver.site_generator.docker_utils import image_exists, run_docker_command
from web_weaver.site_generator.dockerfile_template import render_dockerfile
from web_weaver.site_generator.playwright_checker_template import (
    render_playwright_checker_script,
)
from web_weaver.site_generator.screenshot_capture_template import (
    render_screenshot_capture_script,
)
from web_weaver.site_generator.screenrecording_capture_template import (
    render_screenrecording_capture_script,
)
from web_weaver.site_generator.sanity_checker_template import (
    render_sanity_checker_script,
)
from web_weaver.site_generator.task_prompt import (
    build_entrypoint_script,
    build_task_prompt,
)


CONCEPTS_DIR = Path("Assets") / "Concepts"
BLUEPRINTS_DIR = Path("Assets") / "Blueprints"
DESIGN_PLANS_DIR = Path("Assets") / "DesignPlans"

DEFAULT_BASE_IMAGE = "node:22-slim"
DEFAULT_PORT = 3000
IMAGE_TAG_PREFIX = "web-weaver-sitegen"


def build_image(
    task_id: str,
    *,
    tag: str | None = None,
    base_image: str = DEFAULT_BASE_IMAGE,
    force: bool = False,
    no_cache: bool = False,
) -> str:
    image_tag = tag or default_image_tag(task_id)
    validate_image_tag(image_tag)

    if image_exists(image_tag) and not force:
        return image_tag

    with tempfile.TemporaryDirectory(prefix=f"web-weaver-sitegen-{task_id}-") as temp_dir:
        context_dir = Path(temp_dir)
        prepare_env(task_id, context_dir=context_dir, base_image=base_image)
        command = ["docker", "build", "-t", image_tag]
        if no_cache:
            command.append("--no-cache")
        command.append(str(context_dir))
        run_docker_command(command)

    return image_tag


def prepare_env(
    task_id: str,
    *,
    context_dir: Path,
    base_image: str = DEFAULT_BASE_IMAGE,
) -> None:
    validate_task_id(task_id)
    context_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths = resolve_task_artifacts(task_id)
    shutil.copyfile(artifact_paths["concept"], context_dir / "concept.json")
    shutil.copyfile(artifact_paths["blueprint"], context_dir / "blueprint.json")
    shutil.copyfile(artifact_paths["design_plan"], context_dir / "design_plan.json")

    (context_dir / "Dockerfile").write_text(
        render_dockerfile(base_image=base_image),
        encoding="utf-8",
    )
    (context_dir / "task.md").write_text(
        build_task_prompt(task_id),
        encoding="utf-8",
    )
    entrypoint_path = context_dir / "entrypoint.sh"
    entrypoint_path.write_text(build_entrypoint_script(), encoding="utf-8")
    entrypoint_path.chmod(0o755)
    sanity_checker_path = context_dir / "sanity_check.py"
    sanity_checker_path.write_text(render_sanity_checker_script(), encoding="utf-8")
    sanity_checker_path.chmod(0o755)
    playwright_checker_path = context_dir / "playwright_check.js"
    playwright_checker_path.write_text(
        render_playwright_checker_script(),
        encoding="utf-8",
    )
    playwright_checker_path.chmod(0o755)
    screenshot_capture_path = context_dir / "capture_screenshots.js"
    screenshot_capture_path.write_text(
        render_screenshot_capture_script(),
        encoding="utf-8",
    )
    screenshot_capture_path.chmod(0o755)
    screenrecording_capture_path = context_dir / "capture_screenrecordings.js"
    screenrecording_capture_path.write_text(
        render_screenrecording_capture_script(),
        encoding="utf-8",
    )
    screenrecording_capture_path.chmod(0o755)


def resolve_task_artifacts(task_id: str) -> dict[str, Path]:
    artifact_paths = {
        "concept": CONCEPTS_DIR / f"{task_id}.json",
        "blueprint": BLUEPRINTS_DIR / f"{task_id}.json",
        "design_plan": DESIGN_PLANS_DIR / f"{task_id}.json",
    }
    missing_paths = [str(path) for path in artifact_paths.values() if not path.exists()]
    if missing_paths:
        raise FileNotFoundError(
            "Missing site generator input artifact(s): " + ", ".join(missing_paths)
        )
    return artifact_paths


def default_image_tag(task_id: str) -> str:
    validate_task_id(task_id)
    return f"{IMAGE_TAG_PREFIX}-{task_id.lower()}"


def validate_task_id(task_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", task_id):
        raise ValueError(
            "Task id may only contain letters, numbers, underscore, dot, and dash"
        )


def validate_image_tag(tag: str) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,127}", tag):
        raise ValueError(f"Invalid Docker image tag: {tag}")

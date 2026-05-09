from pathlib import Path

from web_weaver.site_generator.attempt_store import (
    SiteGenerationAttempt,
    create_attempt,
    current_timestamp,
    update_metadata,
)
from web_weaver.site_generator.build_env import (
    DEFAULT_BASE_IMAGE,
    DEFAULT_PORT,
    build_image,
    default_image_tag,
)
from web_weaver.site_generator.docker_utils import capture_docker_command


def run_attempt(
    task_id: str,
    *,
    tag: str | None = None,
    base_image: str = DEFAULT_BASE_IMAGE,
    force_build: bool = False,
    no_cache: bool = False,
    timeout_seconds: int = 1800,
    host_port: int = DEFAULT_PORT,
    env_file: Path | None = Path(".env"),
) -> SiteGenerationAttempt:
    image_tag = tag or default_image_tag(task_id)
    attempt = create_attempt(
        task_id,
        image_tag=image_tag,
        timeout_seconds=timeout_seconds,
    )

    try:
        built_tag = build_image(
            task_id,
            tag=image_tag,
            base_image=base_image,
            force=force_build,
            no_cache=no_cache,
        )

        container_name = build_container_name(task_id, attempt.attempt_id)
        command = build_docker_run_command(
            image_tag=built_tag,
            attempt=attempt,
            container_name=container_name,
            timeout_seconds=timeout_seconds,
            host_port=host_port,
            env_file=env_file,
        )
        container_id = capture_docker_command(command)
        update_metadata(
            attempt,
            status="running",
            image_tag=built_tag,
            container_name=container_name,
            container_id=container_id,
            host_port=host_port,
            started_at=current_timestamp(),
        )
    except Exception:
        update_metadata(
            attempt,
            status="failed",
            finished_at=current_timestamp(),
        )
        raise

    return attempt


def build_container_name(task_id: str, attempt_id: str) -> str:
    return f"sitegen-{task_id.lower()}-{attempt_id}"


def build_docker_run_command(
    *,
    image_tag: str,
    attempt: SiteGenerationAttempt,
    container_name: str,
    timeout_seconds: int,
    host_port: int,
    env_file: Path | None,
) -> list[str]:
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{host_port}:{DEFAULT_PORT}",
        "-e",
        f"SITEGEN_AGENT_TIMEOUT_SECONDS={timeout_seconds}",
        "-v",
        f"{attempt.output_dir.resolve()}:/workspace/output",
        "-v",
        f"{attempt.logs_dir.resolve()}:/workspace/logs",
        "-v",
        f"{attempt.validation_dir.resolve()}:/workspace/validation",
    ]

    if env_file and env_file.exists():
        command.extend(["--env-file", str(env_file)])
    else:
        command.extend(["-e", "ANTHROPIC_API_KEY"])

    command.append(image_tag)
    return command

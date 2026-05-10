import os
import random
import time
from pathlib import Path
from typing import Annotated

import typer

from web_weaver.blueprint_generator import generate_blueprints, parse_concept_ids
from web_weaver.layout_engine import generate_design_plans, parse_blueprint_ids
from web_weaver.llm_utils import AnthropicClient
from web_weaver.sampler import sample_concepts
from web_weaver.site_generator import (
    build_image,
    create_attempt,
    default_image_tag,
    image_exists,
    load_metadata,
    run_attempt,
)


app = typer.Typer(help="Web Weaver task generation tools.")


@app.callback()
def callback() -> None:
    """Web Weaver task generation tools."""


@app.command()
def sample(
    n: Annotated[int, typer.Option("--n", min=1, help="Number of concepts to sample.")],
    seed: Annotated[
        int | None, typer.Option("--seed", help="Optional random seed.")
    ] = None,
) -> None:
    """Sample task concepts into Assets/Concepts/."""
    index = sample_concepts(n=n, seed=seed)
    typer.echo(f"Generated {index.count} concepts into Assets/Concepts/")
    typer.echo(f"Seed: {index.seed}")
    typer.echo(f"Index: Assets/Concepts/index.json")


@app.command()
def test_llm(
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="Anthropic model to call. Defaults to ANTHROPIC_MODEL or Claude Sonnet 4.5.",
        ),
    ] = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
    max_tokens: Annotated[
        int,
        typer.Option("--max-tokens", min=1, help="Maximum response tokens."),
    ] = 200,
) -> None:
    """Make a small Anthropic API test call with a random prompt."""
    prompts = [
        "In one sentence, describe a surreal website for a moonlit bakery.",
        "Give me three concise names for a fictional design-to-code benchmark.",
        "Write a tiny product tagline for an AI-powered garden planner.",
        "Describe a homepage hero section for a retro space museum in two sentences.",
    ]
    prompt = random.choice(prompts)
    typer.echo(f"Model: {model}")
    typer.echo(f"Prompt: {prompt}")

    client = AnthropicClient()
    result = client.prompt_llm(
        model=model,
        question=prompt,
        max_tokens=max_tokens,
        temperature=0.7,
        retries=0,
    )
    typer.echo("\nResponse:")
    typer.echo(result["response"])


@app.command()
def blueprint(
    concept_ids: Annotated[
        str,
        typer.Option(
            "--concept-ids",
            help="Comma-separated concept IDs, e.g. ww-00001,ww-00002.",
        ),
    ],
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="Anthropic model to call. Defaults to ANTHROPIC_MODEL or Claude Sonnet 4.6.",
        ),
    ] = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    max_tokens: Annotated[
        int,
        typer.Option("--max-tokens", min=1000, help="Maximum response tokens."),
    ] = 128000,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print generated blueprints instead of writing."),
    ] = False,
) -> None:
    """Generate SiteBlueprint artifacts from sampled concepts."""
    parsed_concept_ids = parse_concept_ids(concept_ids)
    typer.echo(f"Generating {len(parsed_concept_ids)} blueprint(s)")
    blueprints = generate_blueprints(
        parsed_concept_ids,
        model=model,
        max_tokens=max_tokens,
        dry_run=dry_run,
    )

    for generated_blueprint in blueprints:
        if dry_run:
            typer.echo(generated_blueprint.model_dump_json(indent=2))
        else:
            typer.echo(f"Wrote Assets/Blueprints/{generated_blueprint.id}.json")


@app.command()
def design(
    blueprint_ids: Annotated[
        str,
        typer.Option(
            "--blueprint-ids",
            help="Comma-separated blueprint IDs, e.g. ww-00001,ww-00002.",
        ),
    ],
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="Anthropic model to call. Defaults to ANTHROPIC_MODEL or Claude Sonnet 4.6.",
        ),
    ] = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    max_tokens: Annotated[
        int,
        typer.Option("--max-tokens", min=1000, help="Maximum response tokens."),
    ] = 16000,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print generated design plans instead of writing."),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Write rejected LLM drafts to Assets/Debug for inspection.",
        ),
    ] = False,
) -> None:
    """Generate DesignPlan artifacts from site blueprints."""
    parsed_blueprint_ids = parse_blueprint_ids(blueprint_ids)
    typer.echo(f"Generating {len(parsed_blueprint_ids)} design plan(s)")
    started_at = time.perf_counter()
    design_plans = generate_design_plans(
        parsed_blueprint_ids,
        model=model,
        max_tokens=max_tokens,
        dry_run=dry_run,
        debug=debug,
    )

    for generated_design_plan in design_plans:
        if dry_run:
            typer.echo(generated_design_plan.model_dump_json(indent=2))
        else:
            typer.echo(f"Wrote Assets/DesignPlans/{generated_design_plan.id}.json")

    elapsed_seconds = time.perf_counter() - started_at
    typer.echo(f"Elapsed: {elapsed_seconds:.2f}s")


@app.command()
def sitegen_build_image(
    task_id: Annotated[
        str,
        typer.Option("--id", help="Task ID to bake into a site generator image."),
    ],
    tag: Annotated[
        str | None,
        typer.Option("--tag", help="Optional Docker image tag."),
    ] = None,
    base_image: Annotated[
        str,
        typer.Option("--base-image", help="Base Docker image for the agent runtime."),
    ] = "node:22-slim",
    force: Annotated[
        bool,
        typer.Option("--force", help="Rebuild even if the image already exists."),
    ] = False,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Pass --no-cache to docker build."),
    ] = False,
) -> None:
    """Build a task-specific headless-agent site generator Docker image."""
    image_tag = tag or default_image_tag(task_id)
    already_exists = image_exists(image_tag)
    built_tag = build_image(
        task_id,
        tag=image_tag,
        base_image=base_image,
        force=force,
        no_cache=no_cache,
    )
    if already_exists and not force:
        typer.echo(f"Image already exists: {built_tag}")
    else:
        typer.echo(f"Built image: {built_tag}")


@app.command()
def sitegen_create_attempt(
    task_id: Annotated[
        str,
        typer.Option("--id", help="Task ID to create a persisted attempt for."),
    ],
    tag: Annotated[
        str | None,
        typer.Option("--tag", help="Optional Docker image tag to record."),
    ] = None,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout-seconds", min=1, help="Agent timeout in seconds."),
    ] = 1800,
) -> None:
    """Create a persisted site-generation attempt directory."""
    attempt = create_attempt(
        task_id,
        image_tag=tag,
        timeout_seconds=timeout_seconds,
    )
    metadata = load_metadata(attempt)
    typer.echo(f"Created attempt: {attempt.path}")
    typer.echo(f"Attempt ID: {metadata.attempt_id}")
    typer.echo(f"Input: {attempt.input_dir}")
    typer.echo(f"Output: {attempt.reference_site_dir}")
    typer.echo(f"Logs: {attempt.logs_dir}")


@app.command()
def sitegen_attempt_run(
    task_id: Annotated[
        str,
        typer.Option("--id", help="Task ID to run through the site generator."),
    ],
    tag: Annotated[
        str | None,
        typer.Option("--tag", help="Optional Docker image tag."),
    ] = None,
    base_image: Annotated[
        str,
        typer.Option("--base-image", help="Base Docker image for the agent runtime."),
    ] = "node:22-slim",
    force_build: Annotated[
        bool,
        typer.Option("--force-build", help="Rebuild even if the image already exists."),
    ] = False,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Pass --no-cache to docker build."),
    ] = False,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout-seconds", min=1, help="Agent timeout in seconds."),
    ] = 1800,
    host_port: Annotated[
        int,
        typer.Option("--host-port", min=1, max=65535, help="Host port to map to container port 3000."),
    ] = 3000,
    env_file: Annotated[
        Path | None,
        typer.Option("--env-file", help="Optional Docker env-file containing ANTHROPIC_API_KEY."),
    ] = Path(".env"),
) -> None:
    """Create an attempt, build/check the image, and start the agent container."""
    attempt = run_attempt(
        task_id,
        tag=tag,
        base_image=base_image,
        force_build=force_build,
        no_cache=no_cache,
        timeout_seconds=timeout_seconds,
        host_port=host_port,
        env_file=env_file,
    )
    metadata = load_metadata(attempt)
    typer.echo(f"Attempt: {attempt.path}")
    typer.echo(f"Container: {metadata.container_name}")
    typer.echo(f"Container ID: {metadata.container_id}")
    typer.echo(f"URL: http://localhost:{metadata.host_port}")
    typer.echo(f"Claude log: {attempt.logs_dir / 'claude_stream.jsonl'}")
    typer.echo(f"Entrypoint log: {attempt.logs_dir / 'entrypoint.log'}")


def main() -> None:
    app()

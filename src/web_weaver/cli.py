import os
import random
from typing import Annotated

import typer

from web_weaver.blueprint_generator import generate_blueprints, parse_concept_ids
from web_weaver.llm_utils import AnthropicClient
from web_weaver.sampler import sample_concepts


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
    ] = 8000,
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


def main() -> None:
    app()

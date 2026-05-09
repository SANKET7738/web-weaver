from typing import Annotated

import typer

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


def main() -> None:
    app()

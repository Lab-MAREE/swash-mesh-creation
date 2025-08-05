from pathlib import Path
from typing import Literal, cast

import typer

from . import main

##########
# public #
##########


def run_cli() -> None:
    """
    Main entry point for the CLI application.

    This function initializes the CLI and runs it.
    """
    cli = _init_cli()
    cli()


###########
# private #
###########


def _init_cli() -> typer.Typer:
    """
    Initialize the CLI application with commands.

    Returns
    -------
    typer.Typer
        Configured Typer CLI object with registered commands
    """
    cli = typer.Typer(
        context_settings={"help_option_names": ["-h", "--help"]},
        pretty_exceptions_enable=False,
        pretty_exceptions_show_locals=False,
    )
    cli.command("create")(_create_mesh)
    cli.command("c", hidden=True)(_create_mesh)
    cli.command("apply")(_apply_mesh)
    cli.command("a", hidden=True)(_apply_mesh)
    return cli


def _create_mesh(
    swash_dir: str = typer.Argument(
        ...,
        help="Directory containing the swash input files (INPUT, bathymetry.txt and gauge_positions.txt)",
    ),
    lc_fine: float = typer.Option(
        5.0, "--lc-fine", "-f", help="Mesh size at coast line"
    ),
    lc_coarse: float = typer.Option(
        100.0, "--lc-coarse", "-c", help="Mesh size at deepest part"
    ),
    interpolation: int = typer.Option(
        1,
        "--interpolation",
        "-i",
        help="Interpolation order for mesh size in water: 1 (linear), 2 (quadratic) or 3 (cubic)",
    ),
) -> None:
    # Validate interpolation method
    valid_methods = [1, 2, 3]
    if interpolation not in valid_methods:
        typer.echo(
            f"Error: Invalid interpolation order '{interpolation}'. "
            f"Must be one of: {', '.join(map(str,valid_methods))}",
            err=True,
        )
        raise typer.Exit(1)

    main.create_mesh(
        Path(swash_dir),
        lc_fine=lc_fine,
        lc_coarse=lc_coarse,
        interpolation=interpolation,
    )


def _apply_mesh(
    swash_dir: str = typer.Argument(
        ...,
        help="Directory containing the swash input files (INPUT, bathymetry.txt and gauge_positions.txt)",
    ),
) -> None:
    main.apply_mesh(Path(swash_dir))

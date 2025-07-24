from pathlib import Path

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
) -> None:
    main.create_mesh(Path(swash_dir))


def _apply_mesh(
    swash_dir: str = typer.Argument(
        ...,
        help="Directory containing the swash input files (INPUT, bathymetry.txt and gauge_positions.txt)",
    ),
) -> None:
    main.apply_mesh(Path(swash_dir))

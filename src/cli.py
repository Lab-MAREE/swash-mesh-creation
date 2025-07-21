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
    bathymetry_file: str = typer.Argument(..., help="Bathymetry file"),
) -> None:
    bathymetry_file_ = Path(bathymetry_file)
    main.create_mesh(bathymetry_file_)


def _apply_mesh(
    mesh_file: str = typer.Argument(..., help="Mesh file"),
    input_files: list[str] = typer.Argument(
        ...,
        help="Input files to apply the mesh to (can be the INPUT file, gauge positions file or other cgrid files)",
    ),
    in_place: bool = typer.Option(
        False,
        help="If the files should be directly modified or if a copy in the format `mesh_{file}` should be created.",
    ),
) -> None:
    mesh_file_ = Path(mesh_file)
    input_files_ = [Path(file) for file in input_files]
    main.apply_mesh(mesh_file_, input_files_, in_place=in_place)

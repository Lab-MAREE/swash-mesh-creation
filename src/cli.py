import argparse

############
# external #
############


def run_cli() -> None:
    """
    Main entry point for the CLI application.

    This function initializes the CLI and runs it.
    """
    parser = _init_cli()
    args = parser.parse_args()


############
# internal #
############


def _init_cli() -> argparse.ArgumentParser:
    """
    Initialize the CLI application with arguments.

    Returns
    -------
    argparse.ArgumentParser
        Configured ArgumentParser CLI object
    """
    parser = argparse.ArgumentParser(
        description="Transform SWASH input files from cartesian coordinates to unstructured meshes",
        add_help=True,
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing SWASH input files"
    )
    parser.add_argument(
        "-d", "--dimension",
        type=int,
        choices=[1, 2],
        required=True,
        help="Dimension for mesh generation (1 or 2)"
    )
    return parser

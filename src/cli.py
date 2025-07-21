import argparse

from . import main

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

    if args.input_file is None:
        parser.print_help()
        return

    main.convert_files(
        args.input_file,
        args.gauges,
        args.other_input,
        output_dir=args.output_dir,
        in_place=args.in_place,
    )


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
        description="Transform SWASH input files from cartesian coordinates "
        + "to unstructured meshes",
        add_help=True,
    )
    parser.add_argument(
        "input_file", type=str, nargs="?", help="SWASH INPUT file"
    )
    parser.add_argument(
        "output_dir",
        type=str,
        nargs="?",
        help="Optional directory where to save the modified files. Must be given if "
        + "not --in-place.",
    )
    parser.add_argument(
        "-g",
        "--gauges",
        type=str,
        default=None,
        help="File containing gauge positions (will try to read from INPUT "
        + "if not given)",
    )
    parser.add_argument(
        "-i",
        "--other-input",
        nargs="*",
        default=[],
        help="Other input files with a series or grid of values",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        default=False,
        help="If all input files should be directly modified instead of a "
        + "copy created elsewhere",
    )
    return parser

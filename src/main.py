from pathlib import Path

##########
# public #
##########


def convert_files(
    input_file: Path | str,
    gauge_positions_file: Path | str | None = None,
    other_files: list[Path | str] = [],
    *,
    output_dir: Path | None = None,
    in_place: bool = False,
) -> None:
    """
    Converts the given input files.

    Parameters
    ----------
    input_file : Path
        SWASH INPUT file
    gauge_positions_file : Path | None
        File containing the positions of each gauge.
    other_files : list[Path]
        A list of other input files where each file is a series or a grid of
        values
    output_dir : Path | None (default : None)
        Directory where to save the converted input files. Must be given if
        in_place is False
    in_place : bool
        If the given files should be directly modified instead of a copy
        created

    """
    if output_dir is None and not in_place:
        raise ValueError(
            "If `in_place` is False, an `output_dir` must be given."
        )

    input_file = (
        Path(input_file) if isinstance(input_file, str) else input_file
    )
    gauge_positions_file = (
        Path(gauge_positions_file)
        if isinstance(gauge_positions_file, str)
        else gauge_positions_file
    )
    other_files = [
        Path(file) if isinstance(file, str) else file for file in other_files
    ]

    _verify_files(input_file, gauge_positions_file, other_files)


###########
# private #
###########


def _verify_files(
    input_file: Path,
    gauge_positions_file: Path | None,
    other_files: list[Path],
) -> None:
    for file in [input_file, gauge_positions_file, *other_files]:
        if file is not None and not file.exists():
            raise FileNotFoundError(f"The file `{file}` doesn't exist.")

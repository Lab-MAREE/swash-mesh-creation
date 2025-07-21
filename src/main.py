from pathlib import Path

##########
# public #
##########


def create_mesh(bathymetry_file: Path) -> None:
    _verify_file_existence([bathymetry_file])


def apply_mesh(
    mesh_file: Path, input_files: list[Path], *, in_place: bool = False
) -> None:
    _verify_file_existence([mesh_file, *input_files])


###########
# private #
###########


def _verify_file_existence(files: list[Path]) -> None:
    missing = [file for file in files if not file.exists()]
    if missing:
        raise FileNotFoundError(
            "The following files don't exist: {}".format(
                ", ".join(str(file) for file in files)
            )
        )

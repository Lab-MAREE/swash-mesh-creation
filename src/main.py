import shutil
from pathlib import Path

from . import mesh, swash

##########
# public #
##########


def create_mesh(
    swash_dir: Path,
    *,
    lc_fine: float,
    lc_coarse: float,
    interpolation: int = 1,
) -> None:
    _verify_file_existence(
        [
            swash_dir / "INPUT",
            swash_dir / "bathymetry.txt",
        ]
    )

    bathymetry, porosity, resolution = swash.read_params(swash_dir)

    mesh.create_mesh(
        bathymetry,
        resolution,
        lc_fine=lc_fine,
        lc_coarse=lc_coarse,
        interpolation=interpolation,
        porosity=porosity,
    )


def apply_mesh(swash_dir: Path) -> None:
    _verify_file_existence(
        [
            swash_dir / "INPUT",
            swash_dir / "bathymetry.txt",
            swash_dir / "mesh.node",
            swash_dir / "mesh.ele",
        ]
    )

    shutil.copy(swash_dir / "INPUT", swash_dir / "INPUT.bkp")

    swash.apply_mesh_to_input_files(swash_dir)


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

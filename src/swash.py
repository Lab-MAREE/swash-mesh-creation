from pathlib import Path

import numpy as np
import scipy.interpolate

##########
# public #
##########


def read_params(
    swash_dir: Path,
) -> tuple[np.ndarray, np.ndarray | None, tuple[float, float]]:
    bathymetry = np.loadtxt(swash_dir / "bathymetry.txt").astype(np.float64)
    if (swash_dir / "porosity.txt").exists():
        porosity = np.loadtxt(swash_dir / "porosity.txt").astype(np.float64)
    else:
        porosity = None
    _, (x_resolution, y_resolution) = _get_input_dimensions(
        swash_dir / "INPUT"
    )
    if bathymetry.ndim != 2:
        raise ValueError("Mesh creation is only available for a 2D context.")
    return bathymetry, porosity, (x_resolution, y_resolution)


def extract_shoreline_boundary(
    bathymetry: np.ndarray, resolution: tuple[float, float]
) -> list[tuple[float, float]]:
    x_resolution, y_resolution = resolution

    points: list[tuple[float, float]] = []

    for j in range(bathymetry.shape[0] - 1):
        for i in range(bathymetry.shape[1] - 1):
            corners = (
                bathymetry[j, i],
                bathymetry[j + 1, i],
                bathymetry[j, i + 1],
                bathymetry[j + 1, i + 1],
            )
            if min(corners) <= 0 and max(corners) > 0:
                points.append((i * x_resolution, j * y_resolution))

    return sorted(points)


def extract_breakwaters(
    porosity: np.ndarray | None, resolution: tuple[float, float]
) -> list[tuple[float, float]]:
    if porosity is None:
        return []

    x_resolution, y_resolution = resolution

    return [
        (j * x_resolution, i * y_resolution)
        for i in range(porosity.shape[0])
        for j in range(porosity.shape[1])
        if porosity[i, j] != 1
    ]


def apply_mesh_to_input_files(swash_dir: Path) -> None:
    # bathymetry, porosity, resolution, _ = read_params(swash_dir)
    # nodes, _ = _read_mesh_nodes(swash_dir)
    _apply_mesh_to_input_file(swash_dir)
    # _apply_mesh_to_bathymetry(
    #     swash_dir, bathymetry, porosity, resolution, nodes
    # )


###########
# private #
###########


def _get_input_dimensions(
    path: Path,
) -> tuple[tuple[float, float], tuple[float, float]]:
    with open(path) as f:
        for line in f:
            if line.startswith("INPGRID BOTTOM"):
                line_ = line.strip().split()
                x_cells = int(line_[5])
                y_cells = int(line_[6])
                x_resolution = float(line_[7])
                y_resolution = float(line_[8])

    return (x_cells, y_cells), (x_resolution, y_resolution)


def _read_mesh_nodes(
    swash_dir: Path,
) -> tuple[np.ndarray, np.ndarray]:
    nodes: list[tuple[float, float]] = []
    node_ids: list[int] = []
    with open(swash_dir / "mesh.node") as f:
        f.readline()  # skip header
        for line in f:
            line_ = line.strip().split()
            node_ids.append(int(line_[0]))
            nodes.append((float(line_[1]), float(line_[2])))
    return np.array(nodes), np.array(node_ids)


def _apply_mesh_to_input_file(swash_dir: Path) -> None:
    with open(swash_dir / "INPUT") as f:
        lines = f.readlines()
    with open(swash_dir / "INPUT", "w") as f:
        for line in lines:
            if line.startswith("CGRID"):
                f.write("CGRID UNSTRUCTURED\n")
                f.write("READGRID UNSTRUC TRIANGLE 'mesh'\n")
            elif line.startswith("BOUND"):
                if "EAST" in line:
                    f.write(line.replace("EAST", "SIDE 3 CCW"))
                elif "SOUTH" in line:
                    f.write(line.replace("SOUTH", "SIDE 4 CCW"))
                elif "WEST" in line:
                    f.write(line.replace("WEST", "SIDE 1 CCW"))
                elif "NORTH" in line:
                    f.write(line.replace("NORTH", "SIDE 2 CCW"))
                else:
                    f.write(line)
            elif line.startswith("SPONGELAYER"):
                if "EAST" in line:
                    f.write(line.replace("EAST", "3"))
                elif "SOUTH" in line:
                    f.write(line.replace("SOUTH", "4"))
                elif "WEST" in line:
                    f.write(line.replace("WEST", "1"))
                elif "NORTH" in line:
                    f.write(line.replace("NORTH", "2"))
                else:
                    f.write(line)
            # elif line.startswith("INPGRID"):
            #     f.write(f"INPGRID {line.split()[1]} UNSTRUCTURED\n")
            else:
                f.write(line)


def _apply_mesh_to_bathymetry(
    swash_dir: Path,
    bathymetry: np.ndarray,
    porosity: np.ndarray | None,
    resolution: tuple[float, float],
    nodes: np.ndarray,
) -> None:
    x_resolution, y_resolution = resolution
    bathymetry_positions = np.hstack(
        [
            np.tile(
                np.arange(bathymetry.shape[1]), bathymetry.shape[0]
            ).reshape(-1, 1)
            * x_resolution,
            np.repeat(
                np.arange(bathymetry.shape[0]), bathymetry.shape[1]
            ).reshape(-1, 1)
            * y_resolution,
        ]
    )
    bathymetry_values = bathymetry.reshape(-1)
    bathymetry = scipy.interpolate.griddata(
        bathymetry_positions, bathymetry_values, nodes
    )
    with open("bathymetry.txt", "w") as f:
        for val in bathymetry:
            f.write(f"{val:.3f}\n")

    if porosity is not None:
        porosity_positions = np.hstack(
            [
                np.tile(
                    np.arange(porosity.shape[1]), porosity.shape[0]
                ).reshape(-1, 1)
                * x_resolution,
                np.repeat(
                    np.arange(porosity.shape[0]), porosity.shape[1]
                ).reshape(-1, 1)
                * y_resolution,
            ]
        )
        porosity_values = porosity.reshape(-1)
        porosity = scipy.interpolate.griddata(
            porosity_positions, porosity_values, nodes
        )
        with open("porosity.txt", "w") as f:
            for val in porosity:
                f.write(f"{val:.3f}\n")

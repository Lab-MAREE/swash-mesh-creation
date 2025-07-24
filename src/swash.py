from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import scipy.interpolate

from src import utils

##########
# public #
##########


def read_bathymetry(swash_dir: Path) -> tuple[np.ndarray, tuple[float, float]]:
    bathymetry = np.loadtxt(swash_dir / "bathymetry.txt").astype(np.float64)
    _, (x_resolution, y_resolution) = _get_input_dimensions(
        swash_dir / "INPUT"
    )
    if bathymetry.ndim != 2:
        raise ValueError("Mesh creation is only available for a 2D context.")
    return bathymetry, (x_resolution, y_resolution)


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


def create_diagram(swash_dir: Path) -> go.Figure:
    bathymetry = np.loadtxt(swash_dir / "bathymetry.txt").astype(np.float64)
    gauges = np.loadtxt(swash_dir / "gauge_positions.txt")
    (x_cells, y_cells), (x_resolution, y_resolution) = _get_input_dimensions(
        swash_dir / "INPUT"
    )
    x_edges, y_edges = _get_mesh(swash_dir / "INPUT")
    shoreline = extract_shoreline_boundary(
        bathymetry, (x_resolution, y_resolution)
    )

    if bathymetry.ndim != 2:
        raise ValueError("The diagram implementation needs a 2d bathymetry.")
    if gauges.ndim != 2:
        raise ValueError(
            "The diagram implementation needs the gauges to have positions for x and y."
        )

    x = np.arange(0, (x_cells + 1) * x_resolution, x_resolution)
    y = np.arange(0, (y_cells + 1) * y_resolution, y_resolution)

    min_depth = bathymetry.min()
    max_depth = bathymetry.max()

    return go.Figure(
        [
            go.Contour(
                x=x,
                y=y,
                z=bathymetry,
                name="Bathymetry",
                colorbar_title="Bathymetry",
                hoverinfo="skip",
                line_width=0,
                colorscale=[
                    (0, "#f9e2af"),
                    ((0 - min_depth) / (max_depth - min_depth), "#f9e2af"),
                    (
                        (0 - min_depth) / (max_depth - min_depth) + 1e-16,
                        "#a3bfe9",
                    ),
                    (1, "#0d2a59"),
                ],
            ),
            go.Scatter(
                x=gauges[:, 0],
                y=gauges[:, 1],
                text=[f"G{i+1}" for i in range(gauges.shape[0])],
                textfont_color="black",
                textposition="top center",
                mode="markers+text",
                name="Wave gauges",
                marker={
                    "color": utils.plotting.named_colours["red"],
                    "symbol": "diamond",
                    "size": 10,
                },
            ),
            go.Scatter(
                x=[x[0] for x in shoreline],
                y=[x[1] for x in shoreline],
                mode="lines",
                name="Shoreline",
                hoverinfo="skip",
                line={
                    "color": utils.plotting.named_colours["orange"],
                    "width": 2,
                },
            ),
            go.Scatter(
                x=x_edges,
                y=y_edges,
                mode="lines",
                line={
                    "color": utils.plotting.named_colours["lavender"],
                    "width": 0.25,
                },
                name="Mesh",
                hoverinfo="skip",
            ),
        ],
        {
            "template": utils.plotting.template,
            "height": 750,
            "width": 750,
            "xaxis": {
                "title": "X distance (m)",
                "range": (x[0], x[-1]),
            },
            "yaxis": {
                "title": "Y distance (m)",
                "range": (y[0], y[-1]),
            },
            "showlegend": True,
            "legend": {
                "x": 0.99,
                "y": 0.99,
                "xanchor": "right",
                "yanchor": "top",
            },
        },
    )


def apply_mesh_to_input_files(swash_dir: Path) -> None:
    bathymetry, resolution = read_bathymetry(swash_dir)
    bathymetry = _convert_bathymetry(bathymetry, resolution)
    nodes, node_ids, is_boundary = _read_mesh_nodes(swash_dir)
    _apply_mesh_to_bathymetry(swash_dir, bathymetry, nodes)


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


def _get_mesh(path: Path) -> tuple[list[float], list[float]]:
    with open(path) as f:
        for line in f:
            if line.startswith("CGRID"):
                if "REGULAR" in line:
                    line_ = line.strip().split()
                    x_start = float(line_[2])
                    y_start = float(line_[3])
                    x_end = float(line_[5])
                    y_end = float(line_[6])
                    x_cells = int(line_[7])
                    y_cells = int(line_[8])
                    mesh = _get_rectangular_mesh(
                        np.linspace(x_start, x_end, x_cells),
                        np.linspace(y_start, y_end, y_cells),
                    )

    return mesh


def _get_rectangular_mesh(
    x: np.ndarray, y: np.ndarray
) -> tuple[list[float | None], list[float | None]]:
    x_edges = [
        # horizontal edges
        *[
            x_
            for i in range(x.shape[0] - 1)
            for _ in range(y.shape[0])
            for x_ in (x[i], x[i + 1], None)
        ],
        # vertical edges
        *[
            x_
            for i in range(x.shape[0])
            for _ in range(y.shape[0] - 1)
            for x_ in (x[i], x[i], None)
        ],
    ]
    y_edges = [
        *[
            y_
            for _ in range(x.shape[0] - 1)
            for j in range(y.shape[0])
            for y_ in (y[j], y[j], None)
        ],
        *[
            y_
            for _ in range(x.shape[0])
            for j in range(y.shape[0] - 1)
            for y_ in (y[j], y[j + 1], None)
        ],
    ]
    return x_edges, y_edges


def _convert_bathymetry(
    bathymetry: np.ndarray, resolution: tuple[float, float]
) -> np.ndarray:
    x_resolution, y_resolution = resolution
    return np.array(
        [
            [j * x_resolution, i * y_resolution, bathymetry[i, j]]
            for i in range(bathymetry.shape[0])
            for j in range(bathymetry.shape[1])
        ]
    )


def _read_mesh_nodes(
    swash_dir: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nodes: list[tuple[float, float]] = []
    node_ids: list[int] = []
    is_boundary: list[bool] = []
    with open(swash_dir / "mesh.node") as f:
        f.readline()  # skip header
        for line in f:
            line_ = line.strip().split()
            node_ids.append(int(line_[0]))
            nodes.append((float(line_[1]), float(line_[2])))
            is_boundary.append(line_[3] == "1")
    return np.array(nodes), np.array(node_ids), np.array(is_boundary)


def _apply_mesh_to_bathymetry(
    swash_dir: Path, bathymetry: np.ndarray, nodes: np.ndarray
) -> None:
    bathymetry = scipy.interpolate.griddata(
        bathymetry[:, :2], bathymetry[:, 2], nodes
    )
    with open("bathymetry.txt", "w") as f:
        for val in bathymetry:
            f.write(f"{val:.3f}\n")

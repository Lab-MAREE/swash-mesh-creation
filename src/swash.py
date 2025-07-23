from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from src import utils

##########
# public #
##########


def read_bathymetry(path: Path) -> np.ndarray:
    bathymetry = np.loadtxt(path).astype(np.float64)
    if bathymetry.ndim != 2:
        raise ValueError("Mesh creation is only available for a 2D context.")
    return bathymetry


def create_diagram(swash_dir: Path) -> go.Figure:
    bathymetry = np.loadtxt(swash_dir / "bathymetry.txt").astype(np.float64)
    gauges = np.loadtxt(swash_dir / "gauge_positions.txt")
    (x_cells, y_cells), (x_resolution, y_resolution) = _get_input_dimensions(
        swash_dir / "INPUT"
    )
    x_edges, y_edges = _get_mesh(swash_dir / "INPUT")

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
                    mesh = _create_rectangular_mesh(
                        np.linspace(x_start, x_end, x_cells),
                        np.linspace(y_start, y_end, y_cells),
                    )

    return mesh


def _create_rectangular_mesh(
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

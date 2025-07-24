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


def read_gauge_positions(swash_dir: Path) -> list[tuple[float, float]]:
    return [
        (x, y)
        for x, y in np.loadtxt(swash_dir / "gauge_positions.txt")
        .astype(np.float64)
        .tolist()
    ]


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
    bathymetry: np.ndarray, resolution: tuple[float, float]
) -> list[tuple[float, float]]:
    x_resolution, y_resolution = resolution

    points: list[tuple[float, float]] = []
    
    # Calculate gradients in both directions
    grad_y, grad_x = np.gradient(bathymetry)
    
    # Calculate gradient magnitude and angle
    grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
    
    # Calculate second derivatives to detect gradient changes
    grad2_yy, grad2_yx = np.gradient(grad_y)
    grad2_xy, grad2_xx = np.gradient(grad_x)
    
    # Detect significant gradient changes (curvature)
    # Breakwaters have high curvature where slope changes rapidly
    curvature = np.abs(grad2_xx) + np.abs(grad2_yy)
    
    # Find local maxima in bathymetry (elevated regions)
    rows, cols = bathymetry.shape
    
    # Threshold for significant gradient change
    grad_threshold = np.percentile(grad_magnitude[grad_magnitude > 0], 75)
    curv_threshold = np.percentile(curvature[curvature > 0], 80)
    
    # First, find key breakwater points
    key_points = []
    for j in range(2, rows - 2):
        for i in range(2, cols - 2):
            # Check if this point has significant gradient
            if grad_magnitude[j, i] > grad_threshold:
                # Check if there's significant curvature (gradient change)
                if curvature[j, i] > curv_threshold:
                    # Check if this is an elevated region
                    center_val = bathymetry[j, i]
                    # Look at a 3x3 neighborhood
                    neighborhood = bathymetry[j-1:j+2, i-1:i+2]
                    neighbors_avg = (
                        np.sum(neighborhood) - center_val
                    ) / 8
                    
                    # Check if elevated compared to neighbors
                    if center_val > neighbors_avg + 0.1:  # reduced threshold
                        # Additional check: is this part of a ridge structure?
                        # Check if gradients change sign in nearby points
                        grad_changes_x = (
                            (grad_x[j, i-1] * grad_x[j, i+1] < 0) or
                            (grad_x[j, i-2:i+3].max() * 
                             grad_x[j, i-2:i+3].min() < 0)
                        )
                        grad_changes_y = (
                            (grad_y[j-1, i] * grad_y[j+1, i] < 0) or
                            (grad_y[j-2:j+3, i].max() * 
                             grad_y[j-2:j+3, i].min() < 0)
                        )
                        
                        # If gradient changes sign in either direction
                        if grad_changes_x or grad_changes_y:
                            key_points.append((i, j))
    
    # Create a mask for all breakwater points
    breakwater_mask = np.zeros_like(bathymetry, dtype=bool)
    
    # Mark all key points
    for i, j in key_points:
        breakwater_mask[j, i] = True
    
    # Find all points between key points
    # Group points by row and column
    rows_with_points = {}
    cols_with_points = {}
    
    for i, j in key_points:
        if j not in rows_with_points:
            rows_with_points[j] = []
        rows_with_points[j].append(i)
        
        if i not in cols_with_points:
            cols_with_points[i] = []
        cols_with_points[i].append(j)
    
    # Fill in points between key points in rows
    for j, i_values in rows_with_points.items():
        i_values = sorted(i_values)
        for k in range(len(i_values) - 1):
            i_start, i_end = i_values[k], i_values[k + 1]
            # Fill all points between consecutive key points
            if i_end - i_start < 10:  # reasonable distance
                for i in range(i_start, i_end + 1):
                    breakwater_mask[j, i] = True
    
    # Fill in points between key points in columns
    for i, j_values in cols_with_points.items():
        j_values = sorted(j_values)
        for k in range(len(j_values) - 1):
            j_start, j_end = j_values[k], j_values[k + 1]
            # Fill all points between consecutive key points
            if j_end - j_start < 10:  # reasonable distance
                for j in range(j_start, j_end + 1):
                    breakwater_mask[j, i] = True
    
    # Also connect diagonally adjacent key points
    for idx1, (i1, j1) in enumerate(key_points):
        for idx2 in range(idx1 + 1, len(key_points)):
            i2, j2 = key_points[idx2]
            # Check if points are diagonally close
            if abs(i2 - i1) <= 5 and abs(j2 - j1) <= 5:
                # Fill rectangle between points
                i_min, i_max = min(i1, i2), max(i1, i2)
                j_min, j_max = min(j1, j2), max(j1, j2)
                for j in range(j_min, j_max + 1):
                    for i in range(i_min, i_max + 1):
                        # Check if this point is elevated enough
                        if bathymetry[j, i] > 14.5:  # threshold
                            breakwater_mask[j, i] = True
    
    # Convert mask to list of points
    for j in range(rows):
        for i in range(cols):
            if breakwater_mask[j, i]:
                points.append((i * x_resolution, j * y_resolution))
    
    return points


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

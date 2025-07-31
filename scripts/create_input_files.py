import argparse
import math
from pathlib import Path
from typing import Literal, assert_never

import jinja2
import numpy as np
import plotly.graph_objects as go

template = {
    "layout": go.Layout(
        {
            "title": {
                "xanchor": "center",
                "x": 0.5,
                "font": {"color": "#cdd6f4", "size": 16},
            },
            "font": {
                "color": "#cdd6f4",
            },
            "xaxis": {
                "gridcolor": "#313244",
                "linecolor": "#a6adc8",
                "automargin": True,
                "title_font": {"color": "#cdd6f4"},
                "tickfont": {"color": "#a6adc8"},
            },
            "yaxis": {
                "gridcolor": "#313244",
                "linecolor": "#a6adc8",
                "automargin": True,
                "title_font": {"color": "#cdd6f4"},
                "tickfont": {"color": "#a6adc8"},
            },
            "paper_bgcolor": "#1e1e2e",  # base
            "plot_bgcolor": "#181825",  # mantle
            "colorway": [
                "#89b4fa",  # blue
                "#f38ba8",  # red
                "#a6e3a1",  # green
                "#fab387",  # peach
                "#cba6f7",  # mauve
                "#94e2d5",  # teal
                "#f9e2af",  # yellow
                "#74c7ec",  # sapphire
                "#eba0ac",  # maroon
                "#b4befe",  # lavender
            ],
            "legend": {
                "font": {"color": "#cdd6f4"},
                "bgcolor": "#313244",  # surface0
                "bordercolor": "#89b4fa",  # blue
                "borderwidth": 1,
            },
            "legend_traceorder": "normal",
            "hovermode": "closest",
        }
    )
}


def main() -> None:
    dimensions = (2000.0, 1500.0)
    resolution = (10.0, 10.0)
    breakwater_height = 1.0

    args = _parse_args()
    _create_input_files(
        Path(args.path),
        args.shape,
        args.depth,
        args.elevation,
        args.wave,
        args.breakwaters,
        dimensions,
        resolution,
        breakwater_height,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Directory where to create the files")
    parser.add_argument(
        "-s",
        "--shape",
        choices=["s", "d"],
        default="s",
        help="Shape of the shore : straight (s) or diagonal (d)",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=float,
        default="2.0",
        help="Maxium depth at the southern boundary",
    )
    parser.add_argument(
        "-e",
        "--elevation",
        type=float,
        default="2.0",
        help="Maxium elevation at the northern boundary",
    )
    parser.add_argument(
        "-w",
        "--wave",
        type=float,
        default="1.0",
        help="Significant wave height",
    )
    parser.add_argument(
        "-b",
        "--breakwaters",
        action="store_true",
        default=False,
        help="If breakwaters should be added (5 breakwaters will be added "
        + "1/3 of the distance between the shore and edge)",
    )
    return parser.parse_args()


def _create_input_files(
    path: Path,
    shape: Literal["s", "d"],
    depth: float,
    elevation: float,
    wave_height: float,
    add_breakwaters: bool,
    dimensions: tuple[float, float],
    resolution: tuple[float, float],
    breakwater_height: float,
) -> None:
    n_cells = (
        math.ceil(dimensions[0] / resolution[0]),
        math.ceil(dimensions[1] / resolution[1]),
    )
    resolution = (
        round(dimensions[0] / n_cells[0], 3),
        round(dimensions[1] / n_cells[1], 3),
    )
    _create_input_file(
        path,
        depth,
        wave_height,
        add_breakwaters,
        dimensions,
        resolution,
        n_cells,
    )
    bathymetry = _create_bathymetry(shape, depth, elevation, n_cells)
    shoreline = _extract_shoreline(bathymetry)
    if add_breakwaters:
        bathymetry, porosity = _add_breakwaters(
            bathymetry, shape, shoreline, resolution, breakwater_height
        )
    else:
        porosity = None
    np.savetxt(path / "bathymetry.txt", bathymetry)
    if porosity is not None:
        np.savetxt(path / "porosity.txt", porosity)
    diagram = _create_diagram(bathymetry, resolution, shoreline)
    diagram.write_image(path / "diagram.png")


def _create_input_file(
    path: Path,
    depth: float,
    wave_height: float,
    add_breakwaters: bool,
    dimensions: tuple[float, float],
    resolution: tuple[float, float],
    n_cells: tuple[int, int],
) -> None:
    with open(Path(__file__).parent / "INPUT_template") as f:
        template = jinja2.Template(f.read())
    with open(path / "INPUT", "w") as f:
        f.write(
            template.render(
                depth=depth,
                wave_height=wave_height,
                add_breakwaters=add_breakwaters,
                x_dim=dimensions[0],
                y_dim=dimensions[1],
                x_cells=n_cells[0],
                y_cells=n_cells[1],
                x_resolution=resolution[0],
                y_resolution=resolution[1],
            )
        )


def _create_bathymetry(
    shape: Literal["s", "d"],
    depth: float,
    elevation: float,
    n_cells: tuple[int, int],
) -> np.ndarray:
    if shape == "s":
        return np.concat(
            [
                np.tile(
                    np.linspace(
                        depth, 0, math.ceil((n_cells[1] + 1) / 5 * 4)
                    ).reshape(-1, 1),
                    (1, n_cells[0] + 1),
                ),
                np.tile(
                    np.linspace(
                        0, -elevation, math.ceil((n_cells[1] + 1) / 5)
                    )[1:].reshape(
                        -1, 1
                    ),  # remove the repeated 0 line
                    (1, n_cells[0] + 1),
                ),
            ]
        )
    elif shape == "d":
        shore_point = math.floor(min(n_cells) / 5)
        dist_top_left_to_shore = 2 * shore_point
        dist_bottom_right_to_shore = 2 * (max(n_cells) + 1 - shore_point)
        return np.array(
            [
                [
                    (
                        -elevation
                        + elevation * (i + j) / dist_top_left_to_shore
                        if max(i, j) <= shore_point
                        else depth
                        * ((i - shore_point) + (j - shore_point))
                        / dist_bottom_right_to_shore
                    )
                    for j in range(n_cells[0] + 1)
                ]
                for i in range(n_cells[1], -1, -1)
            ]
        )
    else:
        assert_never(shape)


def _add_breakwaters(
    bathymetry: np.ndarray,
    shape: Literal["s", "d"],
    shoreline: list[tuple[int, int]],
    resolution: tuple[float, float],
    breakwater_height: float,
) -> tuple[np.ndarray, np.ndarray]:
    n_cells = (bathymetry.shape[1], bathymetry.shape[0])
    if shape == "s":
        porosity = np.ones_like(bathymetry)
        length = math.ceil(n_cells[0] / 10)
        space_between = math.floor(n_cells[0] - 5 * length) / 6
        y_position = math.ceil(
            np.arange(n_cells[1])[bathymetry[:, 0] == 0][0] * 2 / 3
        )
        for i in range(5):
            x_position = math.ceil(space_between * (1 + i) + length * i)
            bathymetry[
                y_position - 1 : y_position + 2,
                x_position : x_position + length,
            ] -= breakwater_height
            bathymetry[
                y_position - 2 : y_position,
                x_position : x_position + length,
            ] -= (
                breakwater_height / 2
            )
            bathymetry[
                y_position + 1 : y_position + 2,
                x_position : x_position + length,
            ] -= (
                breakwater_height / 2
            )
            bathymetry[
                y_position - 1 : y_position + 2,
                [x_position - 1, x_position + 1],
            ] -= (
                breakwater_height / 2
            )
            porosity[
                y_position - 1 : y_position + 2,
                x_position - 1 : x_position + 1,
            ] = 0.4
        return bathymetry, porosity
    elif shape == "d":
        porosity = np.ones_like(bathymetry)
        length = math.ceil(len(shoreline) / 10)
        space_between = math.floor(len(shoreline) - 5 * length) / 6
        breakwater_distance = math.floor(
            min(shoreline[0][1], n_cells[0] - shoreline[-1][0]) * 1 / 3
        )
        x_distance = math.floor(
            breakwater_distance / max(n_cells) * n_cells[0]
        )
        y_distance = math.floor(
            breakwater_distance / max(n_cells) * n_cells[1]
        )
        for i in range(5):
            for point in shoreline[
                math.ceil(space_between * (1 + i) + length * i) : math.ceil(
                    space_between * (1 + i) + length * i
                )
                + length
            ]:
                bathymetry[
                    point[1] - y_distance,
                    point[0] + x_distance,
                ] -= breakwater_height
                bathymetry[
                    point[1] - y_distance - 1,
                    point[0] + x_distance + 1,
                ] -= breakwater_height
                bathymetry[
                    point[1] - y_distance + 1,
                    point[0] + x_distance - 1,
                ] -= breakwater_height
                bathymetry[
                    point[1] - y_distance + 2,
                    point[0] + x_distance - 2,
                ] -= (
                    breakwater_height / 2
                )
                bathymetry[
                    point[1] - y_distance - 2,
                    point[0] + x_distance + 2,
                ] -= (
                    breakwater_height / 2
                )
                porosity[
                    point[1] - breakwater_distance,
                    point[0] + breakwater_distance,
                ] = 0.4
                porosity[
                    point[1] - breakwater_distance - 1,
                    point[0] + breakwater_distance + 1,
                ] = 0.4
                porosity[
                    point[1] - breakwater_distance + 1,
                    point[0] + breakwater_distance - 1,
                ] = 0.4
                porosity[
                    point[1] - y_distance + 2,
                    point[0] + x_distance - 2,
                ] = 0.4
                porosity[
                    point[1] - y_distance - 2,
                    point[0] + x_distance + 2,
                ] = 0.4
            for point in (
                shoreline[math.ceil(space_between * (1 + i) + length * i) - 1],
                shoreline[
                    math.ceil(space_between * (1 + i) + length * i) + length
                ],
            ):
                bathymetry[
                    point[1] - y_distance,
                    point[0] + x_distance,
                ] -= (
                    breakwater_height / 2
                )
                bathymetry[
                    point[1] - y_distance - 1,
                    point[0] + x_distance + 1,
                ] -= (
                    breakwater_height / 2
                )
                bathymetry[
                    point[1] - y_distance + 1,
                    point[0] + x_distance - 1,
                ] -= (
                    breakwater_height / 2
                )
                bathymetry[
                    point[1] - y_distance + 2,
                    point[0] + x_distance - 2,
                ] -= (
                    breakwater_height / 2
                )
                bathymetry[
                    point[1] - y_distance - 2,
                    point[0] + x_distance + 2,
                ] -= (
                    breakwater_height / 2
                )
                porosity[
                    point[1] - breakwater_distance,
                    point[0] + breakwater_distance,
                ] = 0.4
                porosity[
                    point[1] - breakwater_distance - 1,
                    point[0] + breakwater_distance + 1,
                ] = 0.4
                porosity[
                    point[1] - breakwater_distance + 1,
                    point[0] + breakwater_distance - 1,
                ] = 0.4
                porosity[
                    point[1] - y_distance + 2,
                    point[0] + x_distance - 2,
                ] = 0.4
                porosity[
                    point[1] - y_distance - 2,
                    point[0] + x_distance + 2,
                ] = 0.4

        return bathymetry, porosity
    else:
        assert_never(shape)


def _create_diagram(
    bathymetry: np.ndarray,
    resolution: tuple[float, float],
    shoreline: list[tuple[int, int]],
) -> go.Figure:
    x = np.arange(0, (bathymetry.shape[1] + 1) * resolution[0], resolution[0])
    y = np.arange(0, (bathymetry.shape[0] + 1) * resolution[1], resolution[1])

    depth = bathymetry.max()
    elevation = bathymetry.min()

    return go.Figure(
        [
            go.Contour(
                x=x,
                y=y,
                z=np.clip(bathymetry, elevation, None),
                name="Bathymetry",
                colorbar_title="Bathymetry",
                hoverinfo="skip",
                line_width=0,
                colorscale=[
                    (0, "#efb02a"),
                    ((0 - elevation) / (depth - elevation) - 0.05, "#f9e2af"),
                    ((0 - elevation) / (depth - elevation), "#a3bfe9"),
                    (1, "#0d2a59"),
                ],
                colorbar={
                    "dtick": 1,
                },
            ),
            go.Scatter(
                x=[x[0] * resolution[0] for x in shoreline],
                y=[x[1] * resolution[1] for x in shoreline],
                mode="lines",
                name="Shoreline",
                hoverinfo="skip",
                line={
                    "color": "#fab387",
                    "width": 2,
                },
            ),
        ],
        {
            "template": template,
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


def _extract_shoreline(bathymetry: np.ndarray) -> list[tuple[int, int]]:
    return sorted(
        [
            (j, i)
            for i in range(bathymetry.shape[0])
            for j in range(bathymetry.shape[1])
            if bathymetry[i, j] == 0
        ]
    )


if __name__ == "__main__":
    main()

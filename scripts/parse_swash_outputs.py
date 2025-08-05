import argparse
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import scipy.interpolate
import scipy.io

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
    args = _parse_args()
    path = Path(args.path)

    bathymetry = np.loadtxt(path / "bathymetry.txt")
    resolution = _extract_resolution(path)
    shoreline = _extract_shoreline(bathymetry)

    n_cells = (bathymetry.shape[1], bathymetry.shape[0])

    times, wave_field = _read_wave_field(path, n_cells, resolution)
    np.save(path / "times.npy", times)
    np.save(path / "wave_field.npy", wave_field)

    fig = _create_animation(
        bathymetry,
        resolution,
        shoreline,
        times,
        wave_field,
        time_per_frame=10.0,
    )
    fig.write_html(path / "water_level_animation.html")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Directory containing the swash files")
    return parser.parse_args()


def _read_wave_field(
    path: Path, n_cells: tuple[int, int], resolution: tuple[float, float]
) -> tuple[np.ndarray, np.ndarray]:
    path = path / "wave_field.mat"
    if not path.exists():
        print(
            "\033[1m\033[91m[!]\033[0m "
            + "SWASH must be run successfully to create the wave_field.mat "
            + f"file which doesn't exist in {path}."
        )
    _data = scipy.io.loadmat(path)
    data = [
        (_parse_time(key), val)
        for key, val in _data.items()
        if key.startswith("Watlev")
    ]
    times = np.array([time for time, _ in data])
    wave_field = np.concatenate(
        [np.expand_dims(field, 0) for _, field in data], 0
    )
    return times, wave_field


def _parse_time(time: str) -> float:
    time = time.replace("Watlev_", "").replace("_", ".")
    return int(time[:2]) * 3600 + int(time[2:4]) * 60 + float(time[4:])


def _extract_resolution(path: Path) -> tuple[float, float]:
    with open(path / "INPUT") as f:
        for line in f:
            if line.startswith("INPGRID BOTTOM"):
                line_ = line.split()
                x_resolution = float(line_[7])
                y_resolution = float(line_[8])
                return (x_resolution, y_resolution)
    raise RuntimeError("Couldn't find resolution in INPUT file.")


def _extract_shoreline(bathymetry: np.ndarray) -> list[tuple[int, int]]:
    return sorted(
        [
            (j, i)
            for i in range(bathymetry.shape[0])
            for j in range(bathymetry.shape[1])
            if bathymetry[i, j] == 0
        ]
    )


def _create_animation(
    bathymetry: np.ndarray,
    resolution: tuple[float, float],
    shoreline: list[tuple[int, int]],
    times: np.ndarray,
    wave_field: np.ndarray,
    *,
    time_per_frame: float = 5.0,
) -> go.Figure:
    x = np.arange(0, (bathymetry.shape[1] + 1) * resolution[0], resolution[0])
    y = np.arange(0, (bathymetry.shape[0] + 1) * resolution[1], resolution[1])

    depth = bathymetry.max()
    elevation = bathymetry.min()
    # make the waves clearer by scaling the wave field
    bathymetry = wave_field * 3 + np.expand_dims(bathymetry, 0)

    frame_indices: list[int] = [0]
    for i in range(1, times.shape[0]):
        if times[i] - times[frame_indices[-1]] >= time_per_frame:
            frame_indices.append(i)
    frame_indices.append(times.shape[0] - 1)

    frames = [
        go.Heatmap(
            x=x,
            y=y,
            z=bathymetry[i],
            name="Bathymetry",
            colorbar_title="Bathymetry",
            colorscale=[
                (0, "#efb02a"),
                ((0 - elevation) / (depth - elevation) - 0.05, "#f9e2af"),
                ((0 - elevation) / (depth - elevation), "#a3bfe9"),
                (1, "#0d2a59"),
            ],
            colorbar={
                "dtick": 1,
            },
            zmin=elevation.min(),
            zmax=depth.max(),
        )
        for i in frame_indices
    ]

    return go.Figure(
        frames[0],
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
            "updatemenus": [
                {
                    "type": "buttons",
                    "showactive": False,
                    "x": 0.5,
                    "xanchor": "center",
                    "y": 1.02,
                    "yanchor": "bottom",
                    "direction": "left",
                    "pad": {"r": 10, "t": 10},
                    "buttons": [
                        {
                            "label": "Play",
                            "method": "animate",
                            "args": [
                                None,
                                {
                                    "frame": {
                                        "duration": 500,
                                        "redraw": True,
                                    },
                                    "fromcurrent": True,
                                    "transition": {"duration": 0},
                                },
                            ],
                        },
                        {
                            "label": "Pause",
                            "method": "animate",
                            "args": [
                                [None],
                                {
                                    "frame": {"duration": 0, "redraw": False},
                                    "mode": "immediate",
                                    "transition": {"duration": 0},
                                },
                            ],
                        },
                    ],
                }
            ],
            "sliders": [
                {
                    "active": 0,
                    "steps": [
                        {
                            "label": f"{times[i]:.1f}s",
                            "method": "animate",
                            "args": [
                                [str(i)],
                                {
                                    "frame": {"duration": 0, "redraw": True},
                                    "mode": "immediate",
                                    "transition": {"duration": 0},
                                },
                            ],
                        }
                        for i in frame_indices
                    ],
                }
            ],
        },
        frames=[
            go.Frame(
                data=[frame],
                name=str(i),
                layout={"title": f"Time: {times[i]:.1f} s"},
                traces=[0],
            )
            for i, frame in zip(frame_indices, frames, strict=True)
        ],
    )


if __name__ == "__main__":
    main()

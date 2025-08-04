import argparse
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
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
    times, wave_field = _read_wave_field(path)
    np.save(path / "times.npy", times)
    np.save(path / "wave_field.npy", wave_field)

    fig = _create_animation(times, wave_field, time_per_frame=5.0)
    fig.write_html(path / "water_level_animation.html")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Directory containing the swash files")
    return parser.parse_args()


def _read_wave_field(path: Path) -> tuple[np.ndarray, np.ndarray]:
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


def _create_animation(
    times: np.ndarray, wave_field: np.ndarray, time_per_frame: float = 5.0
) -> go.Figure:
    # Flip the wave field vertically to match SWASH coordinate system
    # SWASH uses lower-left origin, but plotly heatmap uses upper-left
    wave_field_flipped = np.flip(wave_field, axis=1)
    
    # Group timesteps into frames of time_per_frame seconds
    frame_indices = []
    current_frame_start = 0
    
    for i in range(len(times)):
        if times[i] - times[current_frame_start] >= time_per_frame:
            frame_indices.append(i - 1)
            current_frame_start = i
    
    # Add the last frame
    if len(frame_indices) == 0 or frame_indices[-1] != len(times) - 1:
        frame_indices.append(len(times) - 1)
    
    frames = []
    for idx in frame_indices:
        frame = go.Frame(
            data=[
                go.Heatmap(
                    z=wave_field_flipped[idx],
                    colorscale="Blues",
                    zmin=wave_field_flipped.min(),
                    zmax=wave_field_flipped.max(),
                    colorbar={"title": "Water Level (m)"},
                )
            ],
            name=str(idx),
            layout={"title": f"Time: {times[idx]:.1f} s"},
        )
        frames.append(frame)

    fig = go.Figure(
        data=[
            go.Heatmap(
                z=wave_field_flipped[0],
                colorscale="Blues",
                zmin=wave_field_flipped.min(),
                zmax=wave_field_flipped.max(),
                colorbar={"title": "Water Level (m)"},
            )
        ],
        frames=frames,
    )

    fig.update_layout(
        template=template,
        title="Water Level Animation",
        xaxis={"title": "X coordinate"},
        yaxis={"title": "Y coordinate"},
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 100, "redraw": True},
                                "fromcurrent": True,
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
        sliders=[
            {
                "active": 0,
                "steps": [
                    {
                        "label": f"{times[idx]:.1f}s",
                        "method": "animate",
                        "args": [
                            [str(idx)],
                            {
                                "frame": {"duration": 0, "redraw": True},
                                "mode": "immediate",
                                "transition": {"duration": 0},
                            },
                        ],
                    }
                    for idx in frame_indices
                ],
            }
        ],
    )

    return fig


if __name__ == "__main__":
    main()

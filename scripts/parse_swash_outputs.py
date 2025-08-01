import argparse
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import scipy.io


def main() -> None:
    args = _parse_args()
    path = Path(args.path)
    times, wave_field = _read_wave_field(path)
    np.savetxt(path / "times.txt", times)
    np.savetxt(path / "wave_field.txt", wave_field)


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


def _create_animation(times: np.ndarray, wave_field: np.ndarray) -> go.Figure:
    pass


if __name__ == "__main__":
    main()

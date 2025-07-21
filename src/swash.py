from pathlib import Path
from typing import NamedTuple


class SwashInput(NamedTuple):
    input: str
    gauge_positions: list[float | tuple[float, float]]
    other_files: dict[str, list[float] | list[list[float]]]


def read_swash_input_files(path: Path) -> None:
    pass

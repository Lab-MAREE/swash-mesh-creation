from pathlib import Path
import sys
import itertools
import polars as pl


def parse_swash_outputs(swash_dir: Path) -> None:
    with open(swash_dir / "INPUT") as f:
        for line in f:
            if line.startswith("COMPUTE"):
                line_ = line.split()
                timestep = float(line_[2])

    with open(swash_dir / "gauge_positions.txt") as f:
        gauges = [
            (float(line.strip().split()[0]), float(line.strip().split()[1]))
            for line in f
            if line.strip()
        ]

    with open(swash_dir / "timeseries.txt") as f:
        f.readline(7)
        timeseries_ = [
            {
                key: float(val)
                for key, val in zip(
                    [
                        "water_level",
                        "x_velocity",
                        "y_velocity",
                        "velocity_magnitude",
                        "velocity_direction",
                        "vorticity",
                    ],
                    line.strip().split(),
                    strict=True,
                )
            }
            for line in itertools.islice(f, 7, None)
        ]
    timeseries = pl.concat(
        [
            pl.DataFrame(timeseries_[i :: len(gauges)])
            .with_columns(
                pl.lit(i + 1).alias("gauge"),
                pl.lit(gauge[0]).alias("gauge_x_position"),
                pl.lit(gauge[1]).alias("gauge_y_position"),
            )
            .with_row_index("timestep")
            .with_columns(pl.col("timestep") * timestep)
            for i, gauge in enumerate(gauges)
        ]
    )

    with open(swash_dir / "wave_statistics.txt") as f:
        wave_statistics_: list[dict[str, float | bool | None]] = []
        for i, (line, gauge) in enumerate(
            zip(itertools.islice(f, 7, None), gauges, strict=True)
        ):
            line_ = line.strip().split()
            wave_statistics_.append(
                {
                    "significant_wave_height": (
                        float(line_[0]) if float(line_[0]) != -9 else None
                    ),
                    "wave_setup": (
                        float(line_[1]) if float(line_[1]) != -9 else None
                    ),
                    "breaking_point": (
                        float(line_[2]) == 1
                        if float(line_[2]) != -99
                        else None
                    ),
                    "gauge": i + 1,
                    "gauge_x_position": gauge[0],
                    "gauge_y_position": gauge[1],
                }
            )
    wave_statistics = pl.DataFrame(wave_statistics_)

    timeseries.write_csv(swash_dir / "timeseries.csv")
    wave_statistics.write_csv(swash_dir / "wave_statistics.csv")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_swash_outputs.py <swash_dir>")
        sys.exit()

    parse_swash_outputs(Path(sys.argv[1]))

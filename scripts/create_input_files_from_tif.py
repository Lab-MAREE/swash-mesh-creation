#!/usr/bin/env python3
"""Convert GeoTIFF elevation/bathymetry data to SWASH bathymetry format."""

import argparse
from pathlib import Path

import jinja2
import numpy as np
import plotly.graph_objects as go
import rasterio

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
    """Main entry point for the TIF to bathymetry converter."""
    args = _parse_args()
    _convert_tif_to_bathymetry(
        Path(args.path),
        args.wave_height,
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert GeoTIFF to SWASH bathymetry format and "
        + "create INPUT file"
    )
    parser.add_argument("path", help="Path to input GeoTIFF file")
    parser.add_argument(
        "--wave-height",
        type=float,
        default=1.0,
        help="Significant wave height (default: 1.0)",
    )
    return parser.parse_args()


def _convert_tif_to_bathymetry(
    path: Path,
    wave_height: float,
) -> None:
    """
    Convert a GeoTIFF file to SWASH bathymetry format and create INPUT file.

    Parameters
    ----------
    input_path : Path
        Path to the input GeoTIFF file
    output_dir : Path
        Path to the output directory
    wave_height : float
        Significant wave height
    target_shape : str | None
        Target shape as 'rows,cols' string
    """
    # Create output directory if it doesn't exist
    output_dir = path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read the GeoTIFF file
    with rasterio.open(path) as src:
        # Get the data and metadata
        data = src.read(1)
        rows, cols = data.shape

        # Get resolution from the source (even if resampled, we need it)
        # If no geotransform, assume 10m resolution as default
        transform = src.transform
        x_resolution = abs(transform[0]) if transform[0] != 1.0 else 10.0
        y_resolution = abs(transform[4]) if transform[4] != 1.0 else 10.0

        # Handle NoData values
        if src.nodata is not None:
            # Replace NoData with 0 (assuming it's at shoreline)
            data = np.where(data == src.nodata, 0, data)

        # Convert NaN to 0 as well
        data = np.nan_to_num(data, nan=0.0)

    # Ensure the data is in float format
    bathymetry = data.astype(np.float64)

    # Determine depth as maximum water depth (positive values)
    depth = (
        float(bathymetry[bathymetry > 0].max())
        if (bathymetry > 0).any()
        else 2.0
    )

    # Calculate dimensions
    x_cells = cols - 1  # SWASH uses number of cells, not points
    y_cells = rows - 1
    x_dim = x_cells * x_resolution
    y_dim = y_cells * y_resolution

    bathymetry = np.flip(bathymetry, axis=0)

    # Save bathymetry in SWASH format
    bathymetry_path = output_dir / "bathymetry.txt"
    np.savetxt(bathymetry_path, bathymetry)

    # Create INPUT file using template
    _create_input_file(
        output_dir,
        depth,
        wave_height,
        x_dim,
        y_dim,
        x_cells,
        y_cells,
        x_resolution,
        y_resolution,
    )

    # Create diagram
    diagram = _create_diagram(bathymetry, (x_resolution, y_resolution))
    diagram.write_image(output_dir / "diagram.png")


def _create_input_file(
    output_dir: Path,
    depth: float,
    wave_height: float,
    x_dim: float,
    y_dim: float,
    x_cells: int,
    y_cells: int,
    x_resolution: float,
    y_resolution: float,
) -> None:
    """Create the SWASH INPUT file using the template."""
    # Load template
    template_path = Path(__file__).parent / "INPUT_template"
    with open(template_path) as f:
        template = jinja2.Template(f.read())

    # Write INPUT file
    input_path = output_dir / "INPUT"
    with open(input_path, "w") as f:
        f.write(
            template.render(
                depth=depth,
                wave_height=wave_height,
                add_breakwaters=False,  # TIF files don't have breakwaters
                x_dim=x_dim,
                y_dim=y_dim,
                x_cells=x_cells,
                y_cells=y_cells,
                x_resolution=x_resolution,
                y_resolution=y_resolution,
            )
        )


def _create_diagram(
    bathymetry: np.ndarray, resolution: tuple[float, float]
) -> go.Figure:
    x = np.arange(0, (bathymetry.shape[1] + 1) * resolution[0], resolution[0])
    y = np.arange(0, (bathymetry.shape[0] + 1) * resolution[1], resolution[1])

    depth = bathymetry.max()
    elevation = bathymetry.min()

    # Calculate colorscale positions, ensuring they're Python floats
    if depth != elevation:
        shore_pos = float((0 - elevation) / (depth - elevation))
        shore_pos_minus = max(0.0, shore_pos - 0.05)
    else:
        shore_pos = 0.5
        shore_pos_minus = 0.45

    return go.Figure(
        go.Heatmap(
            x=x,
            y=y,
            z=bathymetry,
            name="Bathymetry",
            colorbar_title="Bathymetry",
            colorscale=[
                (0, "#efb02a"),
                (shore_pos_minus, "#f9e2af"),
                (shore_pos, "#a3bfe9"),
                (1, "#0d2a59"),
            ],
            colorbar={
                "dtick": 1,
            },
        ),
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
        },
    )


if __name__ == "__main__":
    main()

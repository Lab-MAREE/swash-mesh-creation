import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import splev, splprep

named_colours = {
    "blue": "#89b4fa",
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "orange": "#fab387",
    "mauve": "#cba6f7",
    "teal": "#94e2d5",
    "yellow": "#f9e2af",
    "sapphire": "#74c7ec",
    "maroon": "#eba0ac",
    "lavender": "#b4befe",
}

colours = [
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
]

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
            "colorway": colours,
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


class BaieDesBacon:
    """
    Generate realistic bathymetry and shoreline matching actual Baie des Bacon
    """

    def __init__(self):
        # Domain setup (2km x 1.5km to capture the bay)
        self.domain_width = 2000  # metres
        self.domain_height = 1500  # metres

        # High resolution for accurate shoreline
        self.dx = 10  # metres
        self.dy = 10  # metres

        # Create coordinate arrays (origin at bottom-left of bay)
        self.x = np.arange(0, self.domain_width + self.dx, self.dx)
        self.y = np.arange(0, self.domain_height + self.dy, self.dy)
        self.X, self.Y = np.meshgrid(self.x, self.y)

        # Typical depths for the region
        self.max_depth = 5.0  # Maximum depth in bay
        self.nearshore_depth = 1.0  # Typical nearshore depth

    def create_realistic_shoreline(self) -> np.ndarray:
        """
        Create shoreline that matches the actual Baie des Bacon shape
        Based on the curved bay geometry visible in the aerial image
        """

        # Define key shoreline points based on the aerial image
        # Starting from west (left) and going clockwise around the bay

        shoreline_points = np.array(
            [
                # Western approach (deeper water entry)
                [0, 1050],
                [50, 1070],
                [100, 1090],
                [150, 1100],
                # Western shore of bay (curved inward)
                [200, 1110],
                [280, 1130],
                [360, 1150],
                [450, 1170],
                [550, 1180],
                [650, 1185],
                # Head of bay (shallow, curved)
                [750, 1190],
                [850, 1195],
                [950, 1200],
                [1050, 1195],
                [1150, 1190],
                [1250, 1180],
                # Eastern shore (steeper, more linear)
                [1350, 1165],
                [1450, 1145],
                [1550, 1120],
                [1650, 1090],
                [1750, 1050],
                [1850, 1000],
                [1950, 940],
                # Eastern approach (opening to larger water body)
                [2000, 870],
            ]
        )

        # Smooth the shoreline using spline interpolation
        tck, u = splprep(
            [shoreline_points[:, 0], shoreline_points[:, 1]], s=0, per=False
        )

        # Generate smooth shoreline with high resolution
        u_new = np.linspace(0, 1, 200)
        shoreline_smooth = splev(u_new, tck)

        self.shoreline_x = shoreline_smooth[0]
        self.shoreline_y = shoreline_smooth[1]

        return np.column_stack([self.shoreline_x, self.shoreline_y])

    def create_realistic_bathymetry(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Create bathymetry that reflects the typical characteristics
        of a North Shore embayment like Baie des Bacon
        """

        # Create shoreline first
        shoreline = self.create_realistic_shoreline()

        # Initialize bathymetry array
        bathymetry = np.zeros_like(self.X)

        # For each grid point, calculate distance to shoreline
        # and assign depth based on realistic coastal profile

        for i in range(len(self.x)):
            for j in range(len(self.y)):
                point = np.array([self.x[i], self.y[j]])

                # Find closest point on shoreline
                distances = np.sqrt(np.sum((shoreline - point) ** 2, axis=1))
                min_dist_idx = np.argmin(distances)
                shore_distance = distances[min_dist_idx]

                # Determine if point is on land or water
                # Use simple approach: if south of shoreline, it's water
                if self.y[j] < self.shoreline_y[min_dist_idx]:
                    # Water - calculate depth based on distance from shore

                    # Typical North Shore profile: gradual slope then deeper
                    if shore_distance < 50:
                        # Very shallow nearshore (0-1m)
                        depth = shore_distance * 0.02  # 2cm per metre
                    elif shore_distance < 200:
                        # Moderate slope to intermediate depth
                        depth = 1.0 + (shore_distance - 50) * 0.01
                    elif shore_distance < 500:
                        # Gradual deepening
                        depth = 2.5 + (shore_distance - 200) * 0.005
                    else:
                        # Deep water (asymptotic to max depth)
                        depth = 4.0 + (self.max_depth - 4.0) * (
                            1 - np.exp(-(shore_distance - 500) / 200)
                        )

                    # Add some variability based on position in bay
                    # Head of bay is shallower
                    bay_head_factor = np.exp(
                        -((self.x[i] - 1000) ** 2) / (400**2)
                    )
                    depth = depth * (1 - 0.3 * bay_head_factor)

                    # Eastern side slightly deeper (closer to main channel)
                    if self.x[i] > 1200:
                        depth = depth * 1.15

                    bathymetry[j, i] = depth

                else:
                    # Land - set to elevation above water
                    bathymetry[j, i] = -2.0  # 2m above sea level

        # Add some realistic bottom features

        # 1. Deeper channel along eastern side (navigation channel)
        for i in range(len(self.x)):
            if self.x[i] > 1600:
                for j in range(len(self.y)):
                    if bathymetry[j, i] > 0 and self.y[j] < 700:
                        # Add extra depth for deeper channel
                        bathymetry[j, i] += 1.0

        # 2. Shallow bar across bay mouth (common feature)
        bar_y = 600
        bar_width = 100
        for i in range(len(self.x)):
            if 400 < self.x[i] < 1600:  # Across bay mouth
                for j in range(len(self.y)):
                    if abs(self.y[j] - bar_y) < bar_width / 2:
                        if bathymetry[j, i] > 1:
                            # Reduce depth on bar
                            reduction = 1.0 * np.exp(
                                -((self.y[j] - bar_y) ** 2) / (40**2)
                            )
                            bathymetry[j, i] = max(
                                0.5, bathymetry[j, i] - reduction
                            )

        # 3. Rocky patches (areas of reduced depth)
        rocky_areas = [
            (300, 750, 80),  # Western rocky area
            (1400, 820, 60),  # Eastern rocky area
            (800, 880, 50),  # Central rocky patch
        ]

        for rock_x, rock_y, rock_size in rocky_areas:
            for i in range(len(self.x)):
                for j in range(len(self.y)):
                    if bathymetry[j, i] > 0:  # Only in water
                        rock_dist = np.sqrt(
                            (self.x[i] - rock_x) ** 2
                            + (self.y[j] - rock_y) ** 2
                        )
                        if rock_dist < rock_size:
                            rock_effect = 0.8 * np.exp(
                                -(rock_dist**2) / (rock_size / 2) ** 2
                            )
                            bathymetry[j, i] = max(
                                0.3, bathymetry[j, i] - rock_effect
                            )

        # 4. Add breakwaters for wave protection
        bathymetry, porosity = self.add_breakwaters(bathymetry)

        return bathymetry, porosity

    def create_shoreline_boundary(self):
        """
        Create precise shoreline boundary for Gmsh
        """
        bathymetry, _ = self.create_realistic_bathymetry()

        # Find shoreline as zero contour
        shoreline_points = []

        # Trace along the boundary between land and water
        for i in range(len(self.x) - 1):
            for j in range(len(self.y) - 1):
                # Check if we cross the land-water boundary
                corners = [
                    bathymetry[j, i],
                    bathymetry[j + 1, i],
                    bathymetry[j + 1, i + 1],
                    bathymetry[j, i + 1],
                ]

                # If some corners are land (negative) and some water (positive)
                if min(corners) < 0 and max(corners) > 0:
                    # This cell contains shoreline
                    shoreline_points.append([self.x[i], self.y[j]])

        # Remove duplicates and sort
        shoreline_points = np.array(shoreline_points)
        if len(shoreline_points) > 0:
            # Remove duplicates
            unique_points = []
            for point in shoreline_points:
                is_duplicate = False
                for existing in unique_points:
                    if np.linalg.norm(point - existing) < self.dx / 2:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_points.append(point)

            shoreline_points = np.array(unique_points)

        return shoreline_points

    def create_gauge_positions(self) -> np.ndarray:
        """
        Create gauge positions for monitoring water levels
        One gauge at head of bay and two gauges per breakwater (before and after)

        Returns array with shape (11, 2) where columns are [x, y]
        """
        gauge_positions = np.array(
            [
                # Head of bay (shallow area)
                [1000, 1150],
                # Tail of bay (deep area)
                [1000, 200],
                # Left outer breakwater gauges (x=400, y=480)
                [400, 430],  # Before (seaward)
                [400, 530],  # After (landward)
                # Left inner breakwater gauges (x=700, y=500)
                [700, 450],  # Before (seaward)
                [700, 550],  # After (landward)
                # Middle breakwater gauges (x=1000, y=510)
                [1000, 460],  # Before (seaward)
                [1000, 560],  # After (landward)
                # Right inner breakwater gauges (x=1300, y=500)
                [1300, 450],  # Before (seaward)
                [1300, 550],  # After (landward)
                # Right outer breakwater gauges (x=1600, y=480)
                [1600, 430],  # Before (seaward)
                [1600, 530],  # After (landward)
            ]
        )

        return gauge_positions

    def add_breakwaters(
        self, bathymetry: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        # Define breakwater positions and parameters
        # Format: (x, y, height, length, width, angle)
        breakwaters = [
            # Left outer breakwater
            (400, 480, 3.5, 150, 20, 15),
            # Left inner breakwater
            (700, 500, 3.5, 120, 25, 10),
            # Middle breakwater (lower height)
            (1000, 510, 2, 100, 20, 0),
            # Right inner breakwater
            (1300, 500, 3.5, 120, 25, -10),
            # Right outer breakwater
            (1600, 480, 3.5, 150, 20, -15),
        ]

        # Slope ratio (1.75:1 means 1.75 horizontal to 1 vertical)
        slope_ratio = 1.75

        breakwater_porosity = 0.4

        porosity = np.ones_like(bathymetry)

        for (
            bw_x,
            bw_y,
            bw_height,
            bw_length,
            bw_width,
            bw_angle,
        ) in breakwaters:
            # Convert angle to radians
            angle_rad = np.radians(bw_angle)

            # Calculate rotation matrix components
            cos_a = np.cos(angle_rad)
            sin_a = np.sin(angle_rad)

            for i in range(len(self.x)):
                for j in range(len(self.y)):
                    # Only modify water areas
                    if bathymetry[j, i] > 0:
                        # Transform to breakwater local coordinates
                        dx = self.x[i] - bw_x
                        dy = self.y[j] - bw_y

                        # Rotate to align with breakwater
                        local_x = dx * cos_a + dy * sin_a
                        local_y = -dx * sin_a + dy * cos_a

                        # Check if point is within breakwater footprint
                        # Using elliptical shape for more natural appearance
                        if (
                            abs(local_x)
                            < bw_length / 2 + bw_height * slope_ratio
                            and abs(local_y)
                            < bw_width / 2 + bw_height * slope_ratio
                        ):

                            # Calculate distance from breakwater center
                            # Normalize by dimensions
                            norm_x = local_x / (bw_length / 2)
                            norm_y = local_y / (bw_width / 2)
                            norm_dist = np.sqrt(norm_x**2 + norm_y**2)

                            if (
                                norm_dist
                                < 1.0 + bw_height * slope_ratio * 2 / bw_length
                            ):
                                # Calculate elevation based on distance
                                # Core region (flat top)
                                if norm_dist < 0.5:
                                    elevation = bw_height
                                else:
                                    # Sloped region
                                    # Calculate slope distance
                                    slope_dist = (
                                        (norm_dist - 0.5)
                                        * min(bw_length, bw_width)
                                        / 2
                                    )

                                    # Apply slope constraint
                                    max_elevation = (
                                        bw_height - slope_dist / slope_ratio
                                    )

                                    if max_elevation > 0:
                                        # Smooth transition using exponential decay
                                        elevation = max_elevation * np.exp(
                                            -slope_dist
                                            / (bw_height * slope_ratio)
                                        )
                                    else:
                                        elevation = 0

                                # Reduce water depth by breakwater elevation
                                bathymetry[j, i] = bathymetry[j, i] - elevation

                                # add breakwater porosity if not already there
                                porosity[j, i] = min(
                                    porosity[j, i], breakwater_porosity
                                )

        return bathymetry, porosity

    def export_bathymetry_data(self, path: Path) -> np.ndarray:
        """Export bathymetry and shoreline data"""
        bathymetry, porosity = self.create_realistic_bathymetry()
        np.savetxt(path / "bathymetry.txt", bathymetry, fmt="%.3f")
        np.savetxt(path / "porosity.txt", porosity, fmt="%.3f")

        # Export gauge positions
        gauge_positions = self.create_gauge_positions()
        np.savetxt(path / "gauge_positions.txt", gauge_positions, fmt="%.1f")

        return bathymetry

    def visualize_domain(self, path: Path):
        """Visualize the generated bathymetry and shoreline"""
        bathymetry, _ = self.create_realistic_bathymetry()
        gauge_positions = self.create_gauge_positions()

        min_depth = bathymetry.min()
        max_depth = bathymetry.max()

        fig = go.Figure(
            [
                go.Contour(
                    x=self.x,
                    y=self.y,
                    z=bathymetry,
                    colorbar_title="Bathymetry",
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
                    x=gauge_positions[:, 0],
                    y=gauge_positions[:, 1],
                    text=[f"G{i+1}" for i in range(gauge_positions.shape[0])],
                    textfont_color="black",
                    textposition="top center",
                    mode="markers+text",
                    name="Wave gauges",
                    marker={
                        "color": named_colours["red"],
                        "symbol": "diamond",
                        "size": 10,
                    },
                ),
            ],
            {
                "template": template,
                "height": 750,
                "width": 750,
                "xaxis": {
                    "title": "X distance (m)",
                    "range": (self.x[0], self.x[-1]),
                },
                "yaxis": {
                    "title": "Y distance (m)",
                    "range": (self.y[0], self.y[-1]),
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

        fig.write_image(
            path / "baie_des_bacon.png", width=800, height=600, scale=2
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_swash_outputs.py <swash_dir>")
        path = Path()
    else:
        path = Path(sys.argv[1])
    generator = BaieDesBacon()
    bathymetry = generator.export_bathymetry_data(path)
    generator.visualize_domain(path)

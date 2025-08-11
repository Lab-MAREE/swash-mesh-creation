import os
import tempfile

import gmsh
import numpy as np

from . import triangle

##########
# public #
##########


def create_mesh(
    bathymetry: np.ndarray,
    resolution: tuple[float, float],
    *,
    lc_fine: float,
    lc_coarse: float,
    wavelength: float,
    interpolation: int,
    porosity: np.ndarray | None = None,
) -> None:
    x_resolution, y_resolution = resolution

    x_min = 0
    y_min = 0
    x_max = (bathymetry.shape[1] - 1) * x_resolution
    y_max = (bathymetry.shape[0] - 1) * y_resolution

    print("Creating background mesh...")
    # Create background mesh based on bathymetry
    background_mesh_file = _create_background_mesh(
        bathymetry,
        resolution,
        wavelength,
        lc_fine,
        lc_coarse,
        porosity,
        interpolation,
    )
    print("Created background mesh.")

    # initialize gmsh
    gmsh.initialize()
    gmsh.clear()
    gmsh.model.add("coastal_domain")

    # generate mesh in gmsh format
    _generate_mesh(
        background_mesh_file,
        x_min,
        y_min,
        x_max,
        y_max,
        lc_coarse=lc_coarse,
    )

    # write mesh in format understandable by swash
    _write_mesh(
        x_min,
        y_min,
        x_max,
        y_max,
    )

    # Clean up temporary background mesh file
    os.unlink(background_mesh_file)


###########
# private #
###########


def _generate_mesh(
    background_mesh_file: str,
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    *,
    lc_coarse: float,
) -> None:
    # domain corners
    domain_points = [
        gmsh.model.geo.add_point(x_min, y_min, 0, lc_coarse),
        gmsh.model.geo.add_point(x_min, y_max, 0, lc_coarse),
        gmsh.model.geo.add_point(x_max, y_max, 0, lc_coarse),
        gmsh.model.geo.add_point(x_max, y_min, 0, lc_coarse),
    ]

    # domain boundary lines
    domain_lines = [
        gmsh.model.geo.add_line(domain_points[i], domain_points[(i + 1) % 4])
        for i in range(4)
    ]

    # domain curve and surface
    domain_loop = gmsh.model.geo.add_curve_loop(domain_lines)
    gmsh.model.geo.add_plane_surface([domain_loop])

    # synchronize before adding fields
    gmsh.model.geo.synchronize()

    # Merge background mesh and set as background field
    gmsh.merge(background_mesh_file)
    # The merge creates a post-processing view, we need to use it as background mesh
    gmsh.model.mesh.field.add("PostView", 1)
    gmsh.model.mesh.field.setNumber(1, "ViewIndex", 0)
    gmsh.model.mesh.field.setAsBackgroundMesh(1)

    # Set mesh options to use only background mesh
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

    # meshing options
    gmsh.option.setNumber("Mesh.Algorithm", 5)  # delaunay
    gmsh.option.setNumber("Mesh.Smoothing", 10)  # smoothing iterations

    # generate mesh
    gmsh.model.mesh.generate(2)
    gmsh.model.mesh.optimize("Netgen")


def _create_background_mesh(
    bathymetry: np.ndarray,
    resolution: tuple[float, float],
    wavelength: float,
    lc_fine: float,
    lc_coarse: float,
    porosity: np.ndarray | None = None,
    interpolation: int = 1,
) -> str:
    """Create a background mesh based on bathymetry depth.

    Returns the path to the generated .pos file.
    """
    x_resolution, y_resolution = resolution
    # Find maximum depth, handling cases where all bathymetry might be <= 0
    water_depths = bathymetry[bathymetry > 0]
    max_depth = np.max(water_depths) if water_depths.size > 0 else 1.0

    # Calculate distance from shoreline for land points
    shoreline_distances = _calculate_shoreline_distances(
        bathymetry, resolution
    )

    # Identify breakwater locations if porosity data exists
    is_breakwater = np.zeros_like(bathymetry, dtype=bool)
    if porosity is not None:
        is_breakwater = porosity != 1

    # Create temporary file for background mesh
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pos", delete=False
    ) as f:
        f.write('View "background mesh" {\n')

        # Process each grid point
        point_count = 0
        for j in range(bathymetry.shape[0]):
            for i in range(bathymetry.shape[1]):
                x = i * x_resolution
                y = j * y_resolution
                depth = bathymetry[j, i]

                # Breakwaters get fine resolution
                if is_breakwater[j, i]:
                    size = lc_fine
                elif depth <= 0:  # Land or shoreline
                    distance = shoreline_distances[j, i]
                    if distance < wavelength:
                        size = lc_fine
                    else:
                        size = lc_coarse
                else:  # Water
                    # Normalize depth to [0, 1] range
                    depth_ratio = min(depth / max_depth, 1.0)

                    # Apply selected interpolation method
                    size = lc_fine + (lc_coarse - lc_fine) * depth_ratio ** (
                        1 / interpolation
                    )

                # Ensure size is a valid float
                if not np.isfinite(size):
                    size = lc_coarse

                # Write with explicit formatting to avoid locale issues
                f.write(f"SP({x:.6f},{y:.6f},0){{{size:.6f}}};\n")
                point_count += 1

        f.write("};\n")
        f.flush()
        return f.name


def _calculate_shoreline_distances(
    bathymetry: np.ndarray, resolution: tuple[float, float]
) -> np.ndarray:
    """Calculate distance from each land point to nearest shoreline."""
    x_resolution, y_resolution = resolution

    # Create binary mask: 1 for water, 0 for land
    water_mask = (bathymetry > 0).astype(float)

    # Find shoreline pixels (water adjacent to land)
    # Use gradient to find boundaries
    grad_x = np.abs(np.gradient(water_mask, axis=1))
    grad_y = np.abs(np.gradient(water_mask, axis=0))
    shoreline_mask = ((grad_x + grad_y) > 0) & (bathymetry <= 0)

    # Calculate distance from each land point to nearest shoreline
    # Initialize with large values
    distances = np.full_like(bathymetry, 1e10)

    # Set shoreline points to 0 distance
    distances[shoreline_mask] = 0

    # For land points, calculate minimum distance to shoreline
    shoreline_points = np.array(np.where(shoreline_mask)).T
    if len(shoreline_points) > 0:
        for j in range(bathymetry.shape[0]):
            for i in range(bathymetry.shape[1]):
                if bathymetry[j, i] <= 0 and not shoreline_mask[j, i]:
                    # Calculate distances to all shoreline points
                    dists = np.sqrt(
                        ((shoreline_points[:, 0] - j) * y_resolution) ** 2
                        + ((shoreline_points[:, 1] - i) * x_resolution) ** 2
                    )
                    distances[j, i] = np.min(dists)

    return distances


def _write_mesh(
    x_min: float, y_min: float, x_max: float, y_max: float
) -> None:
    gmsh.write("mesh.msh")
    triangle.write_in_triangle_format(x_min, y_min, x_max, y_max)
    gmsh.finalize()

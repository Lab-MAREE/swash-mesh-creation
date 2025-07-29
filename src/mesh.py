"""
Fixed version of mesh.py focusing on the core issues:
1. Correct node ID mapping in triangles
2. Remove unnecessary edge file generation (not needed for SWASH)
3. Ensure proper triangle orientation
"""

import gmsh
import numpy as np

from . import swash

##########
# public #
##########


def create_mesh(
    bathymetry: np.ndarray,
    resolution: tuple[float, float],
    gauge_positions: list[tuple[float, float]],
    *,
    lc_fine: float = 5.0,
    lc_coarse: float = 10.0,
    transition_distance: float = 50.0,
) -> None:
    x_resolution, y_resolution = resolution

    x_min = 0
    y_min = 0
    x_max = (bathymetry.shape[1] - 1) * x_resolution
    y_max = (bathymetry.shape[0] - 1) * y_resolution

    shoreline = swash.extract_shoreline_boundary(bathymetry, resolution)
    breakwaters = swash.extract_breakwaters(bathymetry, resolution)

    # initialize gmsh
    gmsh.initialize()
    gmsh.clear()
    gmsh.model.add("coastal_domain")

    # generate mesh in gmsh format
    _generate_mesh(
        gauge_positions,
        shoreline,
        breakwaters,
        x_min,
        y_min,
        x_max,
        y_max,
        lc_fine=lc_fine,
        lc_coarse=lc_coarse,
        transition_distance=transition_distance,
    )

    # write mesh in format understandable by swash
    _write_mesh(
        x_min,
        y_min,
        x_max,
        y_max,
    )


###########
# private #
###########


def _generate_mesh(
    gauge_positions: list[tuple[float, float]],
    shoreline: list[tuple[float, float]],
    breakwaters: list[tuple[float, float]],
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    *,
    lc_fine: float,
    lc_coarse: float,
    transition_distance: float,
) -> None:
    domain_points = [
        gmsh.model.geo.add_point(x_min, y_min, 0, lc_coarse),
        gmsh.model.geo.add_point(x_min, y_max, 0, lc_coarse),
        gmsh.model.geo.add_point(x_max, y_max, 0, lc_coarse),
        gmsh.model.geo.add_point(x_max, y_min, 0, lc_coarse),
    ]

    # domain boundary lines
    domain_lines = [
        gmsh.model.geo.add_line(domain_points[0], domain_points[1]),
        gmsh.model.geo.add_line(domain_points[1], domain_points[2]),
        gmsh.model.geo.add_line(domain_points[2], domain_points[3]),
        gmsh.model.geo.add_line(domain_points[3], domain_points[0]),
    ]

    # domain curve and surface
    domain_loop = gmsh.model.geo.add_curve_loop(domain_lines)
    gmsh.model.geo.add_plane_surface([domain_loop])

    # specify points of higher resolution
    shoreline_points = [
        gmsh.model.geo.add_point(x, y, 0, lc_fine) for x, y in shoreline
    ]
    finer_points = [
        gmsh.model.geo.add_point(x, y, 0, lc_fine)
        for x, y in sorted(
            set([*breakwaters, *gauge_positions]) - set(shoreline)
        )
    ]

    # lines for the shoreline
    finer_lines = [
        gmsh.model.geo.add_line(point_1, point_2)
        for point_1, point_2 in zip(
            shoreline_points[:-1], shoreline_points[1:], strict=True
        )
    ]

    # synchronize geometry
    gmsh.model.geo.synchronize()

    # distance field from shoreline
    gmsh.model.mesh.field.add("Distance", 1)
    gmsh.model.mesh.field.set_numbers(1, "PointsList", finer_points)
    gmsh.model.mesh.field.set_numbers(1, "CurvesList", finer_lines)

    # threshold field for mesh size transition
    gmsh.model.mesh.field.add("Threshold", 2)
    gmsh.model.mesh.field.set_number(2, "InField", 1)
    gmsh.model.mesh.field.set_number(2, "LcMin", lc_fine)
    gmsh.model.mesh.field.set_number(2, "LcMax", lc_coarse)
    gmsh.model.mesh.field.set_number(2, "DistMin", 0)
    gmsh.model.mesh.field.set_number(2, "DistMax", transition_distance)

    # set threshold field as background mesh field
    gmsh.model.mesh.field.set_as_background_mesh(2)

    # meshing options
    gmsh.option.setNumber("Mesh.Algorithm", 5)  # Delaunay
    gmsh.option.setNumber("Mesh.RecombineAll", 0)  # triangular mesh
    gmsh.option.setNumber("Mesh.Smoothing", 10)  # smooth the mesh
    gmsh.option.setNumber("Mesh.AnisoMax", 1.0)  # limit anisotropy

    # generate mesh
    gmsh.model.mesh.generate(2)

    # optimize mesh quality
    gmsh.model.mesh.optimize("Netgen")


def _write_mesh(
    x_min: float, y_min: float, x_max: float, y_max: float
) -> None:
    gmsh.write("mesh.msh")
    _write_in_triangle_format(x_min, y_min, x_max, y_max)
    gmsh.finalize()


def _write_in_triangle_format(
    x_min: float, y_min: float, x_max: float, y_max: float
) -> None:
    print("Converting to triangle format")

    # Get all nodes from gmsh
    node_tags, node_coords, _ = gmsh.model.mesh.get_nodes()
    node_coords = node_coords.reshape(-1, 3)[:, :2]  # Drop z coordinate

    # Create mapping from gmsh node tags to 1-based indices for output
    gmsh_to_output = {tag: idx + 1 for idx, tag in enumerate(node_tags)}

    # Determine boundary markers for nodes
    tolerance = 1e-10
    boundary_markers = []

    for x, y in node_coords:
        if abs(x - x_min) < tolerance:
            marker = 1  # West
        elif abs(x - x_max) < tolerance:
            marker = 3  # East
        elif abs(y - y_min) < tolerance:
            marker = 4  # South
        elif abs(y - y_max) < tolerance:
            marker = 2  # North
        else:
            marker = 0  # Interior
        boundary_markers.append(marker)

    # Write node file
    with open("mesh.node", "w") as f:
        f.write(f"{len(node_tags)} 2 0 1\n")
        for i, ((x, y), marker) in enumerate(
            zip(node_coords, boundary_markers)
        ):
            f.write(f"{i+1} {x:.10e} {y:.10e} {marker}\n")

    # Get triangles from gmsh
    elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.get_elements(2)

    triangles = []
    for elem_type, node_tags in zip(elem_types, elem_node_tags):
        if elem_type == 2:  # Triangular elements
            # Process triangles in groups of 3 nodes
            for i in range(0, len(node_tags), 3):
                # Get gmsh node tags for this triangle
                gmsh_n1 = node_tags[i]
                gmsh_n2 = node_tags[i + 1]
                gmsh_n3 = node_tags[i + 2]

                # Convert to output node numbers
                n1 = gmsh_to_output[gmsh_n1]
                n2 = gmsh_to_output[gmsh_n2]
                n3 = gmsh_to_output[gmsh_n3]

                # Get coordinates for orientation check
                x1, y1 = node_coords[n1 - 1]
                x2, y2 = node_coords[n2 - 1]
                x3, y3 = node_coords[n3 - 1]

                # Check orientation (positive area = counter-clockwise)
                area = 0.5 * ((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))

                if area > 0:
                    triangles.append((n1, n2, n3))
                else:
                    # Swap to make counter-clockwise
                    triangles.append((n1, n3, n2))

    # Write element file
    with open("mesh.ele", "w") as f:
        f.write(f"{len(triangles)} 3 0\n")
        for i, (n1, n2, n3) in enumerate(triangles):
            f.write(f"{i+1} {n1} {n2} {n3}\n")

    print("Created Triangle format files:")
    print(f"  - mesh.node ({len(node_tags)} nodes)")
    print(f"  - mesh.ele ({len(triangles)} triangles)")

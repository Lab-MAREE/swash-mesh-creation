import gmsh
import numpy as np

from . import swash

##########
# public #
##########


def create_mesh(
    bathymetry: np.ndarray,
    resolution: tuple[float, float],
    gauge_positions: np.ndarray,
    *,
    lc_fine: float = 1.0,
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
    gmsh.option.setNumber("Mesh.Algorithm", 6)  # frontal-delaunay
    gmsh.option.setNumber("Mesh.RecombineAll", 0)  # triangular mesh
    gmsh.option.setNumber("Mesh.Smoothing", 5)  # smooth the mesh

    # generate mesh
    gmsh.model.mesh.generate(2)

    # optimize mesh quality
    gmsh.model.mesh.optimize("Netgen")


def _write_mesh(
    x_min: float, y_min: float, x_max: float, y_max: float
) -> None:
    # write mesh in gmsh format for reference
    gmsh.write("mesh.msh")

    # convert to Triangle format for SWASH
    _write_in_triangle_format(x_min, y_min, x_max, y_max)

    gmsh.finalize()


def _write_in_triangle_format(
    x_min: float, y_min: float, x_max: float, y_max: float
) -> None:
    # get all nodes
    node_tags, node_coords, _ = gmsh.model.mesh.get_nodes()
    n_nodes = len(node_tags)

    # reshape coordinates (x, y, z for each node)
    coords = node_coords.reshape((-1, 3))

    # create mapping from gmsh tags to sequential indices
    tag_to_index = {tag: i + 1 for i, tag in enumerate(node_tags)}
    index_to_coords = {i + 1: coords[i] for i in range(n_nodes)}

    # get 2D elements (triangles)
    element_types, element_tags, node_connectivity = (
        gmsh.model.mesh.get_elements(2)
    )

    # find triangular elements (type 2 in gmsh)
    triangles = []
    for i, elem_type in enumerate(element_types):
        if elem_type == 2:  # 3-node triangle
            # reshape connectivity for this element type
            n_nodes_per_elem = 3
            connectivity = node_connectivity[i].reshape((-1, n_nodes_per_elem))
            triangles.extend(connectivity.tolist())

    triangles = np.array(triangles, dtype=int)
    n_triangles = len(triangles)

    # determine boundary markers based on position
    boundary_markers = np.zeros(n_nodes, dtype=int)

    # tolerance for boundary detection
    tol = 1e-6

    for i, tag in enumerate(node_tags):
        x, y = coords[i, 0], coords[i, 1]

        # Check each boundary separately and assign markers
        if abs(x - x_min) < tol:
            boundary_markers[i] = 1  # west
        elif abs(x - x_max) < tol:
            boundary_markers[i] = 3  # east
        elif abs(y - y_min) < tol:
            boundary_markers[i] = 4  # south
        elif abs(y - y_max) < tol:
            boundary_markers[i] = 2  # north

    # write .node file
    with open("mesh.node", "w") as f:
        # Header: number_of_vertices dimension attributes boundary_markers
        f.write(f"{n_nodes} 2 0 1\n")
        for i in range(n_nodes):
            f.write(
                f"{i+1} {coords[i,0]:.6f} {coords[i,1]:.6f} "
                f"{boundary_markers[i]}\n"
            )

    # ensure triangles are counterclockwise
    ccw_triangles = []
    for tri in triangles:
        # convert gmsh tags to sequential indices
        idx1 = tag_to_index[tri[0]]
        idx2 = tag_to_index[tri[1]]
        idx3 = tag_to_index[tri[2]]

        # get vertices coordinates
        v0 = index_to_coords[idx1]
        v1 = index_to_coords[idx2]
        v2 = index_to_coords[idx3]

        # calculate signed area
        area = 0.5 * (
            (v1[0] - v0[0]) * (v2[1] - v0[1])
            - (v2[0] - v0[0]) * (v1[1] - v0[1])
        )

        if area > 0:
            # already counterclockwise
            ccw_triangles.append([idx1, idx2, idx3])
        else:
            # swap to make counterclockwise
            ccw_triangles.append([idx1, idx3, idx2])

    # write .ele file
    with open("mesh.ele", "w") as f:
        # Header: number_of_triangles nodes_per_triangle attributes
        f.write(f"{n_triangles} 3 0\n")
        for i, tri in enumerate(ccw_triangles):
            f.write(f"{i+1} {tri[0]} {tri[1]} {tri[2]}\n")

    print("Created Triangle format files:")
    print(f"  - mesh.node ({n_nodes} nodes)")
    print(f"  - mesh.ele ({n_triangles} triangles)")

    # Print boundary statistics
    unique, counts = np.unique(boundary_markers, return_counts=True)
    print("\nBoundary marker distribution:")
    for marker, count in zip(unique, counts):
        if marker == 0:
            print(f"  Interior nodes: {count}")
        else:
            sides = {1: "West", 2: "North", 3: "East", 4: "South"}
            print(
                f"  {sides.get(marker, 'Unknown')} boundary (marker {marker}): {count} nodes"
            )

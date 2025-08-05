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
    porosity: np.ndarray | None = None,
    lc_fine: float = 10.0,
    lc_coarse: float = 50.0,
    transition_distance: float = 50.0,
) -> None:
    x_resolution, y_resolution = resolution

    x_min = 0
    y_min = 0
    x_max = (bathymetry.shape[1] - 1) * x_resolution
    y_max = (bathymetry.shape[0] - 1) * y_resolution

    shoreline = swash.extract_shoreline_boundary(bathymetry, resolution)
    breakwaters = swash.extract_breakwaters(porosity, resolution)

    fine_radius = max(x_resolution, y_resolution) / 2

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
        fine_radius=fine_radius,
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
    fine_radius: float,
    transition_distance: float,
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

    # finer resolution close to important points
    _adjust_mesh_sizes(
        # sorted(set([*shoreline, *gauge_positions, *breakwaters])),
        sorted(set([*gauge_positions, *breakwaters])),
        lc_fine=lc_fine,
        lc_coarse=lc_coarse,
        fine_radius=fine_radius,
        transition_distance=transition_distance,
    )

    # meshing options
    gmsh.option.setNumber("Mesh.Algorithm", 5)  # delaunay
    gmsh.option.setNumber("Mesh.Smoothing", 10)  # smoothing iterations

    # generate mesh
    gmsh.model.mesh.generate(2)
    gmsh.model.mesh.optimize("Netgen")


def _adjust_mesh_sizes(
    points: list[tuple[float, float]],
    *,
    lc_fine: float,
    lc_coarse: float,
    fine_radius: float,
    transition_distance: float,
) -> None:
    # MathEval field for size control
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

    field_list: list[int] = []
    for i, (x, y) in enumerate(points):
        gmsh.model.mesh.field.add("Ball", i + 1)
        gmsh.model.mesh.field.setNumber(i + 1, "VIn", lc_fine)
        gmsh.model.mesh.field.setNumber(i + 1, "VOut", lc_coarse)
        gmsh.model.mesh.field.setNumber(i + 1, "Radius", fine_radius)
        gmsh.model.mesh.field.setNumber(i + 1, "XCenter", x)
        gmsh.model.mesh.field.setNumber(i + 1, "YCenter", y)
        field_list.append(i + 1)

    if points:
        gmsh.model.mesh.field.add("MathEval", len(field_list) + 1)
        dist_expr = "1e10"
        for x, y in points:
            dist_expr = f"min({dist_expr}, sqrt((x-{x})^2 + (y-{y})^2))"
        size_expr = f"{lc_fine} + ({lc_coarse}-{lc_fine}) * min(1.0, max(0.0, ({dist_expr}-{fine_radius})/({transition_distance}-{fine_radius})))"
        gmsh.model.mesh.field.setString(len(field_list) + 1, "F", size_expr)
        field_list.append(len(field_list) + 1)

    # Create minimum field
    if field_list:
        gmsh.model.mesh.field.setAsBackgroundMesh(field_list[-1])


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
    nodes, convert_id = _get_triangle_nodes(x_min, y_min, x_max, y_max)
    triangles = _get_triangle_triangles(
        nodes, convert_id, x_min, y_min, x_max, y_max
    )

    with open("mesh.node", "w") as f:
        # header: number_of_vertices dimension attributes boundary_markers
        f.write(f"{nodes.shape[0]} 2 0 1\n")
        for i, (x, y, edge) in enumerate(nodes):
            f.write(f"{i+1} {x:.6f} {y:.6f} {int(edge)}\n")

    with open("mesh.ele", "w") as f:
        # header: number_of_triangles nodes_per_triangle attributes
        f.write(f"{len(triangles)} 3 0\n")
        for i, (node_1, node_2, node_3) in enumerate(triangles):
            f.write(f"{i+1} {node_1+1} {node_2+1} {node_3+1}\n")

    print("Created Triangle format files:")
    print(f"  - mesh.node ({nodes.shape[0]} nodes)")
    print(f"  - mesh.ele ({len(triangles)} triangles)")


def _get_triangle_nodes(
    x_min: float, y_min: float, x_max: float, y_max: float
) -> tuple[np.ndarray, dict[int, int]]:
    node_ids, nodes, _ = gmsh.model.mesh.get_nodes()
    convert_id = {id: i for i, id in enumerate(node_ids)}

    # reshape coordinates (x, y, z for each node) and drop z that's always 0
    nodes = nodes.reshape(-1, 3)[:, :2]

    # 1: west, 2: north, 3: east, 4: south
    edges: list[int] = []
    for x, y in nodes:
        if x == x_min:
            if y < y_max:
                edges.append(1)
            else:
                edges.append(2)
        elif y == y_max:
            if x < x_max:
                edges.append(2)
            else:
                edges.append(3)
        elif x == x_max:
            if y > y_min:
                edges.append(3)
            else:
                edges.append(4)
        elif y == y_min:
            edges.append(4)
        else:
            edges.append(0)

    nodes = np.concatenate(
        [
            nodes,
            np.array(edges).reshape(-1, 1),
        ],
        axis=1,
    )

    return nodes, convert_id


def _get_triangle_triangles(
    nodes: np.ndarray,
    convert_id: dict[int, int],
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
) -> list[tuple[int, int, int]]:
    element_types, element_tags, node_connectivity = (
        gmsh.model.mesh.get_elements(2)
    )

    # find triangular elements (type 2 in gmsh) and the (x, y) coordinates of
    # the corner nodes, and make sure node 1 is the furthest right and down
    triangles_ = [
        sorted(
            (
                (
                    convert_id[node[0]],
                    nodes[convert_id[node[0]]][:2].tolist(),
                ),
                (
                    convert_id[node[1]],
                    nodes[convert_id[node[1]]][:2].tolist(),
                ),
                (
                    convert_id[node[2]],
                    nodes[convert_id[node[2]]][:2].tolist(),
                ),
            ),
            key=lambda node: (-node[1][0], node[1][1]),
        )
        for nodes_, type_ in zip(node_connectivity, element_types, strict=True)
        for node in nodes_.reshape(-1, 3)
        if type_ == 2
    ]

    # ensure triangles are counterclockwise
    triangles: list[tuple[int, int, int]] = []
    for (
        (node_1_id, node_1),
        (node_2_id, node_2),
        (node_3_id, node_3),
    ) in triangles_:
        # Calculate cross product to determine orientation
        # (node_2 - node_1) x (node_3 - node_1)
        cross_product = (node_2[0] - node_1[0]) * (node_3[1] - node_1[1]) - (
            node_2[1] - node_1[1]
        ) * (node_3[0] - node_1[0])

        if cross_product > 0:
            # Already counter-clockwise
            triangles.append((node_1_id, node_2_id, node_3_id))
        else:
            # Clockwise, so swap node_2 and node_3
            triangles.append((node_1_id, node_3_id, node_2_id))

    return triangles

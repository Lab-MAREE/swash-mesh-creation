import gmsh
import numpy as np

##########
# public #
##########


def write_in_triangle_format(
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


###########
# private #
###########


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

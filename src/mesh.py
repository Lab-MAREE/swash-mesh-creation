import gmsh
import numpy as np

from . import swash

##########
# public #
##########


def create_mesh(
    bathymetry: np.ndarray,
    resolution: tuple[float, float],
    *,
    lc_fine: float = 1.0,
    lc_coarse: float = 10.0,
    transition_distance: float = 50.0,
) -> None:
    # initialize gmsh
    gmsh.initialize()
    gmsh.clear()
    gmsh.model.add("coastal_domain")

    # generate mesh in gmsh format
    _generate_mesh(
        bathymetry,
        resolution,
        lc_fine=lc_fine,
        lc_coarse=lc_coarse,
        transition_distance=transition_distance,
    )

    # write mesh in format understandable by swash
    _write_mesh()


###########
# private #
###########


def _generate_mesh(
    bathymetry: np.ndarray,
    resolution: tuple[float, float],
    *,
    lc_fine: float,
    lc_coarse: float,
    transition_distance: float,
) -> None:
    x_resolution, y_resolution = resolution

    shoreline = swash.extract_shoreline_boundary(bathymetry, resolution)

    x_min = 0
    y_min = 0
    x_max = (bathymetry.shape[1] - 1) * x_resolution
    y_max = (bathymetry.shape[0] - 1) * y_resolution

    # domain corner points
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

    # shoreline
    shore_points = [
        gmsh.model.geo.add_point(x, y, 0, lc_fine) for x, y in shoreline
    ]

    # synchronize geometry
    gmsh.model.geo.synchronize()

    # distance field from shoreline
    gmsh.model.mesh.field.add("Distance", 1)
    gmsh.model.mesh.field.set_numbers(1, "PointsList", shore_points)

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


def _write_mesh() -> None:
    # write mesh in gmsh format for reference
    gmsh.write("mesh.msh")

    # convert to Triangle format for SWASH
    _write_in_triangle_format()

    gmsh.finalize()


def _write_in_triangle_format() -> None:
    # get all nodes
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    n_nodes = len(node_tags)

    # reshape coordinates (x, y, z for each node)
    coords = node_coords.reshape((-1, 3))

    # create mapping from gmsh tags to sequential indices
    tag_to_index = {tag: i + 1 for i, tag in enumerate(node_tags)}

    # get 2D elements (triangles)
    element_types, element_tags, node_connectivity = (
        gmsh.model.mesh.getElements(2)
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

    # get boundary information
    # for each node, determine if it's on a boundary
    boundary_markers = np.zeros(n_nodes, dtype=int)

    # get 1D elements (boundary edges)
    edge_types, edge_tags, edge_nodes = gmsh.model.mesh.getElements(1)

    boundary_nodes = set()
    for i, elem_type in enumerate(edge_types):
        if elem_type == 1:  # 2-node line
            nodes = edge_nodes[i]
            boundary_nodes.update(nodes)

    # set boundary markers (1 for boundary nodes, 0 for interior)
    for i, tag in enumerate(node_tags):
        if tag in boundary_nodes:
            boundary_markers[i] = 1

    # write .node file
    # format: <# of vertices> <dimension (2)> <# of attributes> <boundary markers (0 or 1)>
    # followed by: <vertex #> <x> <y> [attributes] [boundary marker]
    with open("mesh.node", "w") as f:
        f.write(f"{n_nodes} 2 0 1\n")
        for i in range(n_nodes):
            # Triangle uses 1-based indexing
            f.write(
                f"{i+1} {coords[i,0]:.6f} {coords[i,1]:.6f} "
                f"{boundary_markers[i]}\n"
            )

    # write .ele file
    # format: <# of triangles> <nodes per triangle (3)> <# of attributes>
    # followed by: <triangle #> <node 1> <node 2> <node 3> [attributes]
    with open("mesh.ele", "w") as f:
        f.write(f"{n_triangles} 3 0\n")
        for i in range(n_triangles):
            # convert gmsh tags to sequential indices (1-based)
            nodes = [tag_to_index[tag] for tag in triangles[i]]
            f.write(f"{i+1} {nodes[0]} {nodes[1]} {nodes[2]}\n")

    print("Created Triangle format files:")
    print(f"  - mesh.node ({n_nodes} nodes)")
    print(f"  - mesh.ele ({n_triangles} triangles)")

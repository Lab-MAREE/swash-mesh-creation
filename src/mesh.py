import gmsh
import numpy as np

from . import swash, triangle

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
    triangle.write_in_triangle_format(x_min, y_min, x_max, y_max)
    gmsh.finalize()

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
    # write mesh
    gmsh.write("mesh.msh")
    gmsh.finalize()

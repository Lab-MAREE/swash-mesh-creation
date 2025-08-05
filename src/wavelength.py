import math

#########
# types #
#########

g = 9.81

##########
# public #
##########


def compute_wavelength(
    wave_period: float,
    water_depth: float,
    *,
    n_iter: int = 10,
    tol: float = 1e-6,
) -> float:
    wavelength = g * wave_period * wave_period / (2 * math.pi)

    if water_depth / wavelength < 0.05:  # shallow water
        wavelength = wave_period * math.sqrt(g * water_depth)
    elif water_depth / wavelength > 0.5:  # deep water
        pass  # initial wavelength is already deep water approximation
    else:  # intermediate water
        for _ in range(n_iter):
            old_wavelength = wavelength
            wavelength = wavelength - _compute_dispersion_derivative(
                wave_period, water_depth, wavelength
            ) / _compute_dispersion(wave_period, water_depth, wavelength)
            if abs(wavelength - old_wavelength) / wavelength < tol:
                break

    return wavelength


###########
# private #
###########


def _compute_dispersion(
    wave_period: float, water_depth: float, wavelength: float
) -> float:
    return wavelength - g * wave_period**2 / (2 * math.pi) * math.tanh(
        2 * math.pi * water_depth / wavelength
    )


def _compute_dispersion_derivative(
    wave_period: float, water_depth: float, wavelength: float
) -> float:
    return (
        g
        * water_depth
        * wave_period**2
        / (
            math.cosh(2 * math.pi * water_depth / wavelength) ** 2
            * wavelength**2
        )
        + 1
    )

import plotly.graph_objects as go

#########
# types #
#########

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

############
# external #
############


def convert_colour(colour: str, *, opacity: float = 1) -> str:
    """
    Convert a hex color to an rgba color string with specified opacity.

    Parameters
    ----------
    colour : str
        Hex color string (e.g., "#fd7f6f")
    opacity : float, default 1
        Opacity value between 0 and 1

    Returns
    -------
    str
        RGBA color string (e.g., "rgba(253,127,111,1)")
    """
    colour = colour.lstrip("#")
    return (
        "rgba("
        + ",".join(str(int(colour[i : i + 2], 16)) for i in (0, 2, 4))
        + f",{opacity})"
    )

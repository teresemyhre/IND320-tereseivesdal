import altair as alt

custom_colors = ["#416287", "#9ecaec", "#5890b7", "#fd9e53", "#ffcea8"]

@alt.theme.register('custom_theme', enable=True)
def custom_theme():
    return alt.theme.ThemeConfig(
        {"config": {"range": {"category": custom_colors}}}
    )

# Function to get color mapping for production groups
def get_color_map():
    return {
        "hydro":   custom_colors[0],
        "wind":    custom_colors[1],
        "solar":   custom_colors[3],  # warmer orange for solar
        "thermal": custom_colors[2],
        "other":   custom_colors[4],
    }
import altair as alt

custom_colors = ["#416287", "#9ecaec", "#5890b7", "#fd9e53", "#ffcea8"]

@alt.theme.register('custom_theme', enable=True)
def custom_theme():
    return alt.theme.ThemeConfig(
        {"config": {"range": {"category": custom_colors}}}
    )
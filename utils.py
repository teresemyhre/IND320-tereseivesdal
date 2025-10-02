import altair as alt

custom_colors = ["#fd9e53", "#ffcea8", "#6CA0DC", "#9ecaec", "#3b97da"]

@alt.theme.register('custom_theme', enable=True)
def custom_theme():
    return alt.theme.ThemeConfig(
        {"config": {"range": {"category": custom_colors}}}
    )
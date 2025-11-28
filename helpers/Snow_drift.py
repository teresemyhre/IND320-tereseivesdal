#!/usr/bin/env python3
"""
Snow drift calculation and visualization module for IND320.

Improvements:
 - Monthly Qt now extends to June 30 of (end_year+1)
 - Yearly Qt bars span July 1 → June 30 exactly
 - Combined plot rewritten for clarity
 - Toggle between overlay vs grouped visualization modes
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from helpers.utils import custom_colors, get_color_map
from plotly.colors import hex_to_rgb

rgb_yearly = hex_to_rgb(custom_colors[1])
rgba_yearly = f"rgba({rgb_yearly[0]}, {rgb_yearly[1]}, {rgb_yearly[2]}, 0.45)"

# --------------------------------------------------------------
# Tabler core functions
# --------------------------------------------------------------
def compute_Qupot(hourly_wind_speeds, dt=3600):
    return sum((u ** 3.8) * dt for u in hourly_wind_speeds) / 233847


def sector_index(direction):
    return int(((direction + 11.25) % 360) // 22.5)


def compute_sector_transport(hourly_wind_speeds, hourly_wind_dirs, dt=3600):
    sectors = [0.0] * 16
    for u, d in zip(hourly_wind_speeds, hourly_wind_dirs):
        sectors[sector_index(d)] += ((u ** 3.8) * dt) / 233847
    return sectors


def compute_snow_transport(T, F, theta, Swe, hourly_wind_speeds, dt=3600):
    Qupot = compute_Qupot(hourly_wind_speeds, dt)
    Qspot = 0.5 * T * Swe
    Srwe = theta * Swe

    if Qupot > Qspot:
        Qinf = 0.5 * T * Srwe
        control = "Snowfall controlled"
    else:
        Qinf = Qupot
        control = "Wind controlled"

    Qt = Qinf * (1 - 0.14 ** (F / T))

    return {
        "Qupot (kg/m)": Qupot,
        "Qspot (kg/m)": Qspot,
        "Srwe (mm)": Srwe,
        "Qinf (kg/m)": Qinf,
        "Qt (kg/m)": Qt,
        "Control": control
    }


# --------------------------------------------------------------
# Year assignment (July → June)
# --------------------------------------------------------------
def assign_season(dt):
    return dt.year if dt.month >= 7 else dt.year - 1


# --------------------------------------------------------------
# Compute yearly Qt (per season)
# --------------------------------------------------------------
def compute_yearly_results(df, T, F, theta):
    results = []

    for s in sorted(df["season"].unique()):
        start = pd.Timestamp(s, 7, 1)
        end = pd.Timestamp(s + 1, 6, 30, 23, 59)

        df_s = df[(df["time"] >= start) & (df["time"] <= end)].copy()
        if df_s.empty:
            continue

        df_s["Swe_hourly"] = df_s.apply(
            lambda r: r["precipitation"] if r["temperature_2m"] < 1 else 0,
            axis=1
        )
        Swe = df_s["Swe_hourly"].sum()
        wind = df_s["wind_speed_10m"].tolist()

        res = compute_snow_transport(T, F, theta, Swe, wind)
        res["season"] = s
        results.append(res)

    return pd.DataFrame(results)


# --------------------------------------------------------------
# 16-sector wind rose mean
# --------------------------------------------------------------
def compute_average_sector(df):
    sectors = []
    for season, grp in df.groupby("season"):
        ws = grp["wind_speed_10m"].tolist()
        wd = grp["wind_direction_10m"].tolist()
        sectors.append(compute_sector_transport(ws, wd))
    return np.mean(sectors, axis=0)


# --------------------------------------------------------------
# Plot: Yearly Qt (bar)
# --------------------------------------------------------------
def make_plotly_Qt_bar(df_yearly):
    Qt_ton = df_yearly["Qt (kg/m)"] / 1000
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_yearly["start"],
        y=Qt_ton,
        width=df_yearly["width_ms"],  # exact bar width (July→June)
        name="Yearly Qt",
        marker_color="rgba(120,140,255,0.45)",
    ))

    fig.update_layout(
        title="Seasonal Snow Transport (Qt)",
        xaxis_title="Snow Season",
        yaxis_title="Qt (tonnes/m)",
        template="plotly_white",
        height=450
    )
    return fig


# --------------------------------------------------------------
# Plot: Wind rose
# --------------------------------------------------------------
def make_plotly_wind_rose(avg_sectors):
    dirs = [
        'N','NNE','NE','ENE','E','ESE','SE','SSE',
        'S','SSW','SW','WSW','W','WNW','NW','NNW'
    ]
    fig = go.Figure()

    fig.add_trace(go.Barpolar(
        r=avg_sectors / 1000,
        theta=dirs,
        marker_color=custom_colors[-1],
        marker_line_color="black"
    ))

    fig.update_layout(
        title="Average Directional Transport (Wind Rose)",
        template="plotly_white",
        polar=dict(
            radialaxis=dict(title="Tonnes/m"),
            angularaxis=dict(direction="clockwise")
        ),
        height=500
    )
    return fig


# --------------------------------------------------------------
# High-level Streamlit wrapper
# --------------------------------------------------------------
def compute_snow_drift_plotly(df_raw, start_year, end_year, T=3000, F=30000, theta=0.5):
    df = df_raw.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None)
    df["season"] = df["time"].apply(assign_season)

    df = df[(df["season"] >= start_year) & (df["season"] <= end_year)]
    if df.empty:
        return None, None, None

    # YEARLY Qt
    df_yearly = compute_yearly_results(df, T, F, theta)

    df_yearly["start"] = df_yearly["season"].apply(lambda s: pd.Timestamp(s, 7, 1))
    df_yearly["end"] = df_yearly["start"] + pd.DateOffset(years=1) - pd.Timedelta(days=1)
    df_yearly["width_ms"] = (df_yearly["end"] - df_yearly["start"]).dt.total_seconds() * 1000
    df_yearly["Qt_yearly"] = df_yearly["Qt (kg/m)"]

    # WIND ROSE
    avg_sectors = compute_average_sector(df)

    fig_Qt = make_plotly_Qt_bar(df_yearly)
    fig_rose = make_plotly_wind_rose(avg_sectors)

    return fig_Qt, fig_rose, df_yearly


# --------------------------------------------------------------
# Monthly + Yearly combined plot (new bonus function)
# --------------------------------------------------------------
def compute_monthly_and_yearly_Qt_plotly(df_raw, year_start, year_end,
                                         T=3000, F=30000, theta=0.5,
                                         mode="overlay"):
    """
    Compute yearly Qt and monthly Qt on a consistent snow-season timeline.
    Each snow year runs from 1 July (year) to 30 June (year+1).

    Parameters
    ----------
    df_raw : DataFrame
        ERA5 dataframe with columns:
        time, temperature_2m, precipitation,
        wind_speed_10m, wind_direction_10m
    year_start : int
        First snow year to include (e.g. 2015 means 2015-07-01 → 2016-06-30)
    year_end : int
        Last snow year to include
    T, F, theta : float
        Tabler snow transport parameters
    mode : {"overlay", "grouped"}
        overlay: time axis with bars + monthly line
        grouped: per-season grouped bars

    Returns
    -------
    fig : plotly.graph_objects.Figure
    df_yearly : DataFrame with yearly Qt
    df_monthly : DataFrame with monthly Qt (aligned to seasons)
    """

    df = df_raw.copy().sort_values("time")
    # Assign snow season
    df["season"] = df["time"].apply(assign_season)

    # Keep only selected seasons
    df = df[(df["season"] >= year_start) & (df["season"] <= year_end)]
    if df.empty:
        return go.Figure(), pd.DataFrame(), pd.DataFrame()

    # ------------------------
    # YEARLY Qt (July–June)
    # ------------------------
    yearly_records = []
    for s in sorted(df["season"].unique()):
        season_start = pd.Timestamp(year=s, month=7, day=1)
        season_end = pd.Timestamp(year=s + 1, month=6, day=30, hour=23, minute=59)

        season_df = df[(df["time"] >= season_start) & (df["time"] <= season_end)]
        if season_df.empty:
            continue

        # SWE: precipitation where temperature < +1°C
        Swe = season_df.apply(
            lambda row: row["precipitation"] if row["temperature_2m"] < 1 else 0,
            axis=1
        ).sum()

        wind = season_df["wind_speed_10m"].tolist()
        out = compute_snow_transport(T, F, theta, Swe, wind)

        yearly_records.append({
            "season": s,
            "Qt_yearly": out["Qt (kg/m)"],
            "season_start": season_start,
            "season_end": season_end
        })

    df_yearly = pd.DataFrame(yearly_records)
    if df_yearly.empty:
        return go.Figure(), df_yearly, pd.DataFrame()

    # Center of each snow season (for bar placement)
    df_yearly["center"] = df_yearly["season_start"] + (
        df_yearly["season_end"] - df_yearly["season_start"]
    ) / 2
    # Bar width = full length of the snow season in milliseconds
    df_yearly["width_ms"] = (
        df_yearly["season_end"] - df_yearly["season_start"]
    ).dt.total_seconds() * 1000.0

    # ------------------------
    # MONTHLY Qt (aligned to seasons)
    # ------------------------
    df["month_start"] = df["time"].dt.to_period("M").dt.to_timestamp()

    monthly_records = []
    for (s, m), g in df.groupby(["season", "month_start"]):
        Swe_m = g.apply(
            lambda row: row["precipitation"] if row["temperature_2m"] < 1 else 0,
            axis=1
        ).sum()
        wind_m = g["wind_speed_10m"].tolist()
        out_m = compute_snow_transport(T, F, theta, Swe_m, wind_m)

        monthly_records.append({
            "season": s,
            "month": m,
            "Qt_monthly": out_m["Qt (kg/m)"]
        })

    df_monthly = pd.DataFrame(monthly_records)

    # ------------------------
    # Build figure
    # ------------------------
    
    fig = go.Figure()

    # Yearly bars (one per snow season, centered in the season)
    fig.add_trace(go.Bar(
        x=df_yearly["center"],
        y=df_yearly["Qt_yearly"],
        width=df_yearly["width_ms"],
        name="Yearly Qt (kg/m)",
        marker_color=rgba_yearly
    ))

    # Monthly Qt as line on same time axis
    if not df_monthly.empty:
        fig.add_trace(go.Scatter(
            x=df_monthly["month"],
            y=df_monthly["Qt_monthly"],
            name="Monthly Qt (kg/m)",
            mode="lines+markers",
            line=dict(color=custom_colors[3], width=2),
            marker=dict(size=5, color=custom_colors[3])
        ))

    fig.update_layout(
        title=dict(
            text="Monthly and Yearly Snow Drift (Qt)",
            # font=dict(size=24)
        ),
        xaxis_title="Calendar time (snow years run July–June)",
        yaxis_title="Qt (kg/m)",
        template="plotly_white",
        legend_title="Component",
        height=500
    )
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,        # move below plot
            xanchor="center",
            x=0.15,
            title_text="",  # optional: remove "Component" text
        )
    )

    return fig, df_yearly, df_monthly
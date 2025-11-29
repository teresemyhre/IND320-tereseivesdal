import streamlit as st
import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
import plotly.graph_objects as go

from helpers.sidebar import global_sidebar
from helpers.functions import download_era5_data, cities_df
from helpers.utils import custom_colors
from helpers.data_loader import load_elhub_data


# -----------------------------------------------------------
# Exogenous cleaning
# -----------------------------------------------------------
def clean_exog(df):
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.interpolate(limit_direction="both")
    return df.fillna(method="ffill").fillna(method="bfill")


# -----------------------------------------------------------
# Cached ERA5 (per year)
# -----------------------------------------------------------
@st.cache_data(show_spinner="Downloading ERA5 weather…")
def load_weather_year(lat, lon, year):
    df = download_era5_data(lat, lon, year)
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None)
    return df.set_index("time")


@st.cache_data(show_spinner="Preparing weather range…")
def load_weather_range(lat, lon, start, end):
    years = range(start.year, end.year + 1)
    dfs = [load_weather_year(lat, lon, y) for y in years]
    df = pd.concat(dfs)
    return df.loc[start:end]


# -----------------------------------------------------------
# Cached energy subset
# -----------------------------------------------------------
@st.cache_data(show_spinner="Filtering Elhub energy data…")
def load_energy_series(area, groups, group_col, train_start, train_end):
    df = load_elhub_data()
    df = df[
        (df["pricearea"] == area) &
        (df[group_col].isin(groups)) &
        (df["starttime"].dt.date >= train_start) &
        (df["starttime"].dt.date <= train_end)
    ]
    ser = df.groupby("starttime")["quantitykwh"].sum()
    return ser.resample("1H").mean().interpolate()


# -----------------------------------------------------------
# Cached SARIMAX fit
# -----------------------------------------------------------
@st.cache_data(show_spinner="Fitting SARIMAX model…")
def fit_sarimax(endog, exog, p, d, q, P, D, Q, s, trend):
    model = SARIMAX(
        endog=endog,
        exog=exog,
        order=(p, d, q),
        seasonal_order=(P, D, Q, s),
        trend=trend,
        enforce_stationarity=False,
        enforce_invertibility=False
    )
    res = model.fit(disp=False, method="powell", maxiter=80,)
    return res


# -----------------------------------------------------------
# Page setup
# -----------------------------------------------------------
st.set_page_config(page_title="SARIMAX Forecasting", page_icon="🔮", layout="wide")

with st.sidebar:
    valid = global_sidebar()
if not valid:
    st.error("Please select at least one group before continuing.")
    st.stop()

area = st.session_state["price_area"]
groups = st.session_state["selected_groups"]
energy_type = st.session_state["energy_type"]

group_col = "productiongroup" if energy_type == "production" else "consumptiongroup"
st.title(f"SARIMAX Forecasting of {energy_type.capitalize()}")


# -----------------------------------------------------------
# Training window
# -----------------------------------------------------------
st.subheader("Training Window & Horizon")

c1, c2 = st.columns(2)
with c1:
    train_start = st.date_input("Training start", pd.Timestamp("2021-01-01"))
    train_end = st.date_input("Training end", pd.Timestamp("2021-03-31"))

with c2:
    forecast_hours = st.number_input("Forecast horizon (hours)", 1, 1000, 168)

weather_vars = [
    "temperature_2m", "precipitation",
    "wind_speed_10m", "wind_gusts_10m",
    "wind_direction_10m"
]

exog_vars = st.multiselect("Exogenous meteorological variables", weather_vars)


# -----------------------------------------------------------
# SARIMAX parameters
# -----------------------------------------------------------
st.subheader("SARIMAX Parameters")

cols = st.columns(8)
p  = cols[0].number_input("AR (p)", 0, 5, 1)
d  = cols[1].number_input("Diff (d)", 0, 2, 0)
q  = cols[2].number_input("MA (q)", 0, 5, 1)
P  = cols[3].number_input("Seasonal AR (P)", 0, 5, 0)
D  = cols[4].number_input("Seasonal Diff (D)", 0, 2, 0)
Q  = cols[5].number_input("Seasonal MA (Q)", 0, 5, 1)
s  = cols[6].selectbox("Season length (s)", [24, 168], index=0)
trend = cols[7].selectbox("Trend", ["n", "c", "t", "ct"], index=1)


# -----------------------------------------------------------
# Load energy & weather
# -----------------------------------------------------------
df_energy = load_energy_series(area, groups, group_col, train_start, train_end)

coords = cities_df[cities_df["price_area"] == area].iloc[0]
lat, lon = coords["latitude"], coords["longitude"]

df_weather = load_weather_range(lat, lon, train_start, train_end)


# -----------------------------------------------------------
# Prepare exogenous
# -----------------------------------------------------------
if exog_vars:
    exog_train = clean_exog(df_weather[exog_vars].reindex(df_energy.index))
else:
    exog_train = None

# Forecast exogenous
if exog_vars:
    horizon_index = pd.date_range(
        df_energy.index[-1] + pd.Timedelta(hours=1),
        periods=forecast_hours,
        freq="1H"
    )
    last_values = exog_train.iloc[-1:]
    exog_future = last_values.reindex(horizon_index, method="ffill")
    exog_future = clean_exog(exog_future)
else:
    exog_future = None


# -----------------------------------------------------------
# RUN MODEL BUTTON
# -----------------------------------------------------------
st.markdown("### Run SARIMAX Model")
run = st.button("🚀 Run Forecast")

if run:

    # Fit model
    results = fit_sarimax(
        df_energy,
        exog_train,
        p, d, q,
        P, D, Q, s,
        trend
    )

    # Forecast
    forecast = results.get_forecast(steps=forecast_hours, exog=exog_future)
    pred = forecast.predicted_mean
    conf = forecast.conf_int()

    # Plot
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_energy.index, y=df_energy,
        mode="lines", name="Historical",
        line=dict(color=custom_colors[1])
    ))

    fig.add_trace(go.Scatter(
        x=pred.index, y=pred,
        mode="lines", name="Forecast",
        line=dict(color=custom_colors[3])
    ))

    fig.add_trace(go.Scatter(
        x=pred.index, y=conf.iloc[:, 0],
        mode="lines", line=dict(width=0),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=pred.index, y=conf.iloc[:, 1],
        mode="lines",
        fill="tonexty",
        fillcolor="rgba(120,120,200,0.2)",
        line=dict(width=0),
        name="Confidence Interval"
    ))

    fig.update_layout(
        template="plotly_white",
        height=600,
        xaxis_title="Time",
        yaxis_title="Energy (kWh)",
        title="SARIMAX Forecast"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.info(f"AIC: **{results.aic:.1f}**, BIC: **{results.bic:.1f}**")

else:
    st.warning("Adjust parameters, then press **Run Forecast** to fit the model.")
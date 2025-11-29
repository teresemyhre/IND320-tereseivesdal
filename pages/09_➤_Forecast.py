import streamlit as st
import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
import plotly.graph_objects as go

from helpers.sidebar import global_sidebar
from helpers.functions import download_era5_data, cities_df
from helpers.utils import custom_colors


# -----------------------------------------------------------
# Utility: Clean exogenous variables
# -----------------------------------------------------------
def clean_exog(df):
    df = df.copy()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.interpolate(limit_direction="both")
    df = df.fillna(method="ffill").fillna(method="bfill")
    return df


# -----------------------------------------------------------
# Cached per-year weather (massive speed-up)
# -----------------------------------------------------------
@st.cache_data(show_spinner="Downloading ERA5 weather (per year)…")
def load_weather_year(lat, lon, year):
    df = download_era5_data(lat, lon, year)
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None)
    return df.set_index("time")


@st.cache_data(show_spinner="Preparing weather for selected training range…")
def load_weather_range_cached(lat, lon, start, end):
    years = range(start.year, end.year + 1)
    frames = [load_weather_year(lat, lon, y) for y in years]
    df = pd.concat(frames)
    return df.loc[start:end]


# -----------------------------------------------------------
# Cache SARIMAX fitting (HUGE speed improvement)
# -----------------------------------------------------------
@st.cache_data(show_spinner="Fitting SARIMAX model…")
def fit_sarimax_cached(endog, exog, order, seasonal_order, trend):
    model = SARIMAX(
        endog=endog,
        exog=exog,
        order=order,
        seasonal_order=seasonal_order,
        trend=trend,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    results = model.fit(disp=False)
    return results


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
elhub = st.session_state["elhub_data"]

group_col = "productiongroup" if energy_type == "production" else "consumptiongroup"
st.title(f"SARIMAX Forecasting of {energy_type.capitalize()}")


# -----------------------------------------------------------
# Training window + horizon
# -----------------------------------------------------------
st.subheader("Training Window and Forecast Horizon")

c1, c2 = st.columns(2)

with c1:
    train_start = st.date_input("Training start date", value=pd.Timestamp("2021-01-01"))
    train_end = st.date_input("Training end date", value=pd.Timestamp("2021-12-31"))

with c2:
    forecast_hours = st.number_input(
        "Forecast horizon (hours ahead)", 1, 1000, 168
    )

    weather_vars_available = [
        "temperature_2m", "precipitation",
        "wind_speed_10m", "wind_gusts_10m",
        "wind_direction_10m"
    ]

    exog_vars = st.multiselect(
        "Exogenous meteorological variables",
        weather_vars_available,
        default=[]
    )


# -----------------------------------------------------------
# SARIMAX parameters
# -----------------------------------------------------------
st.subheader("SARIMAX Parameters")

colA, colB, colC, colD, colE, colF, colG, colH = st.columns(8)

with colA:  ar_order = st.number_input("AR (p)", 0, 5, 1)
with colB:  diff_order = st.number_input("Diff (d)", 0, 2, 0)
with colC:  ma_order = st.number_input("MA (q)", 0, 5, 1)
with colD:  seas_ar = st.number_input("Seasonal AR (P)", 0, 5, 0)
with colE:  seas_diff = st.number_input("Seasonal Diff (D)", 0, 2, 1)
with colF:  seas_ma = st.number_input("Seasonal MA (Q)", 0, 5, 1)
with colG:  seas_period = st.selectbox("Season length (s)", [24, 168], index=0)
with colH:  trend = st.selectbox("Trend", ["n", "c", "t", "ct"], index=1)


# -----------------------------------------------------------
# Energy data
# -----------------------------------------------------------
df_energy = elhub[
    (elhub["pricearea"] == area) &
    (elhub[group_col].isin(groups)) &
    (elhub["starttime"].dt.date >= train_start) &
    (elhub["starttime"].dt.date <= train_end)
]

df_energy = df_energy.groupby("starttime")["quantitykwh"].sum()
df_energy = df_energy.resample("1H").mean().interpolate()


# -----------------------------------------------------------
# Weather data
# -----------------------------------------------------------
row = cities_df[cities_df["price_area"] == area].iloc[0]
lat, lon = row["latitude"], row["longitude"]

df_weather = load_weather_range_cached(lat, lon, train_start, train_end)


# -----------------------------------------------------------
# Exogenous matrices
# -----------------------------------------------------------
if exog_vars:
    exog_train = clean_exog(df_weather[exog_vars].reindex(df_energy.index))
else:
    exog_train = None


# Forecast exogenous
if exog_vars:
    forecast_index = pd.date_range(
        df_energy.index[-1] + pd.Timedelta(hours=1),
        periods=forecast_hours,
        freq="1H"
    )
    last_row = exog_train.iloc[-1:]
    exog_forecast = clean_exog(last_row.reindex(forecast_index, method="ffill"))
else:
    exog_forecast = None


# -----------------------------------------------------------
# Fit SARIMAX (cached!)
# -----------------------------------------------------------
results = fit_sarimax_cached(
    df_energy,
    exog_train,
    order=(ar_order, diff_order, ma_order),
    seasonal_order=(seas_ar, seas_diff, seas_ma, seas_period),
    trend=trend
)


# -----------------------------------------------------------
# Forecast
# -----------------------------------------------------------
forecast = results.get_forecast(steps=forecast_hours, exog=exog_forecast)
pred = forecast.predicted_mean
conf = forecast.conf_int()


# -----------------------------------------------------------
# Plot
# -----------------------------------------------------------
fig = go.Figure()

# history
fig.add_trace(go.Scatter(
    x=df_energy.index, y=df_energy,
    mode="lines",
    name="Historical",
    line=dict(color=custom_colors[1])
))

# forecast
fig.add_trace(go.Scatter(
    x=pred.index, y=pred,
    mode="lines",
    name="Forecast",
    line=dict(color=custom_colors[3])
))

# confidence intervals
fig.add_trace(go.Scatter(
    x=pred.index, y=conf.iloc[:, 0],
    mode="lines", line=dict(width=0),
    showlegend=False
))
fig.add_trace(go.Scatter(
    x=pred.index, y=conf.iloc[:, 1],
    mode="lines",
    fill="tonexty",
    fillcolor="rgba(100,100,200,0.2)",
    line=dict(width=0),
    name="Confidence Interval"
))

fig.update_layout(
    template="plotly_white",
    height=600,
    legend=dict(orientation="h", y=-0.2),
    xaxis_title="Time",
    yaxis_title="Energy (kWh)",
    title="SARIMAX Forecast with Confidence Intervals"
)

st.plotly_chart(fig, use_container_width=True)

st.info(f"AIC: **{results.aic:.1f}**, BIC: **{results.bic:.1f}**")
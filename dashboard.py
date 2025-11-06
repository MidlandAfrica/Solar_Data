# -*- coding: utf-8 -*-
"""
Created on Thu Nov  6 14:03:41 2025

@author: USER
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import StringIO

# ------------------------------
# PAGE CONFIG
# ------------------------------
st.set_page_config(page_title="Solar Performance Dashboard", layout="wide", page_icon="☀️")

# ------------------------------
# LOAD DATA FROM GITHUB
# ------------------------------
DATA_URL = "https://raw.githubusercontent.com/MidlandAfrica/Solar_Data/main/28-09.csv"

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(url=DATA_URL):
    df = pd.read_csv(url)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Standardize column names
    df.rename(columns={
        'solar_production(kw)': 'solar_kw',
        'storage_production(kw)': 'storage_kw',
        'load_consumption(kw)': 'load_kw'
    }, inplace=True)

    # Convert watts to kilowatts (if data in W)
    if df['solar_kw'].max() > 100:  # quick sanity check
        df['solar_kw'] = df['solar_kw'] / 1000
        df['storage_kw'] = df['storage_kw'] / 1000
        df['load_kw'] = df['load_kw'] / 1000

    # Combine date & time into a single datetime
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
    df.sort_values('datetime', inplace=True)

    # Flags
    df['system_status'] = np.where(
        (df['solar_kw'] == 0) & (df['storage_kw'] == 0) & (df['load_kw'] == 0), 'Shutdown', 'Running'
    )

    df['anomaly_flag'] = np.where(
        (df['solar_kw'] == 0) & (df['storage_kw'] == 0) & (df['load_kw'] > 0.01), 'Abnormal', 'Normal'
    )

    return df

data = load_data()

# ------------------------------
# FILTERS
# ------------------------------

st.sidebar.header("Filters")

start_date = st.sidebar.date_input("Start Date", value=data['datetime'].min().date())
end_date = st.sidebar.date_input("End Date", value=data['datetime'].max().date())

status_filter = st.sidebar.multiselect(
    "System Status", options=data['system_status'].unique(), default=list(data['system_status'].unique())
)
anomaly_filter = st.sidebar.multiselect(
    "Anomaly Status", options=data['anomaly_flag'].unique(), default=list(data['anomaly_flag'].unique())
)

filtered = data[
    (data['datetime'].dt.date >= start_date)
    & (data['datetime'].dt.date <= end_date)
    & (data['system_status'].isin(status_filter))
    & (data['anomaly_flag'].isin(anomaly_filter))
]

# ------------------------------
# KPIs
# ------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_load = filtered['load_kw'].sum()
    st.metric("Total Load Consumption (kWh)", f"{total_load:,.2f}")

with col2:
    total_solar = filtered['solar_kw'].sum()
    st.metric("Total Solar Production (kWh)", f"{total_solar:,.2f}")

with col3:
    total_storage = filtered['storage_kw'].sum()
    st.metric("Total Storage Production (kWh)", f"{total_storage:,.2f}")

with col4:
    peak_day = (
        filtered.groupby(filtered['datetime'].dt.date)['load_kw'].sum().idxmax()
        if not filtered.empty
        else None
    )
    st.metric("Peak Load Day", f"{peak_day if peak_day else '-'}")

# ------------------------------
# CHARTS
# ------------------------------

st.markdown("### ⚙️ Energy Performance Overview")

chart_data = filtered.melt(
    id_vars=['datetime'],
    value_vars=['solar_kw', 'storage_kw', 'load_kw'],
    var_name='Parameter',
    value_name='kW'
)

line_chart = (
    alt.Chart(chart_data)
    .mark_line(interpolate='basis')
    .encode(
        x='datetime:T',
        y='kW:Q',
        color='Parameter:N'
    )
    .properties(height=400)
)

st.altair_chart(line_chart, use_container_width=True)

# ------------------------------
# ANOMALY TABLE
# ------------------------------

st.markdown("### ⚠️ Anomaly Records")

anomalies = filtered[filtered['anomaly_flag'] == 'Abnormal']
if anomalies.empty:
    st.success("No anomalies detected during the selected period.")
else:
    st.dataframe(anomalies[['datetime', 'solar_kw', 'storage_kw', 'load_kw', 'system_status', 'anomaly_flag']])

# ------------------------------
# DOWNLOAD SECTION
# ------------------------------

st.markdown("### 💾 Download Data")

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

csv = convert_df(filtered)

col_d1, col_d2 = st.columns(2)

with col_d1:
    st.download_button("Download Filtered Data (CSV)", csv, "filtered_solar_data.csv", "text/csv")

with col_d2:
    st.download_button("Download Full Data (CSV)", convert_df(data), "full_solar_data.csv", "text/csv")

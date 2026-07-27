#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

@st.cache_data
def load_data():
    path = Path(__file__).parent.parent / 'data' / 'co2_emissions.csv'
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-01-01')
    return df

df = load_data()

st.title("CO₂ Emissions Explorer")

with st.sidebar:
    st.header("Filters")

    selected_countries = st.multiselect(
        "Countries", sorted(df['Country'].unique()),
        default=['China', 'United States', 'India', 'Germany']
    )

    if not selected_countries:
        st.warning("Select at least one country.")
        st.stop()

    year_range = st.slider("Year range",
        int(df['Year'].min()), int(df['Year'].max()), (2010, 2020))

filtered = df[
    df['Country'].isin(selected_countries) &
    (df['Year'] >= year_range[0]) &
    (df['Year'] <= year_range[1])
]

st.caption(f"Showing {len(selected_countries)} countries | {len(filtered)} data points")

# ── Coloring logic ────────────────────────────────────────────────────────────
# Rank countries by their CO2_Mt in the LAST year of the filtered range.
# Highest emitter → dark red, Lowest emitter → dark blue, rest → light grey.

last_year = filtered['Year'].max()
last_year_df = filtered[filtered['Year'] == last_year].set_index('Country')['CO2_Mt']

highest = last_year_df.idxmax()
lowest  = last_year_df.idxmin()

COLOR_HIGH = '#C0392B'   # dark red
COLOR_LOW  = '#1A5276'   # dark blue
COLOR_REST = '#CCCCCC'   # light grey

color_map = {}
for country in selected_countries:
    if country == highest:
        color_map[country] = COLOR_HIGH
    elif country == lowest:
        color_map[country] = COLOR_LOW
    else:
        color_map[country] = COLOR_REST

fig = px.line(filtered, x='Year', y='CO2_Mt', color='Country',
              labels={'CO2_Mt': 'CO2 (Mt)'},
              color_discrete_map=color_map)

# Make the highlighted lines thicker so they stand out even more
for trace in fig.data:
    if trace.name in (highest, lowest):
        trace.line.width = 3
    else:
        trace.line.width = 1.5

fig.update_layout(
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family='Arial'),
    title=f"Highest: {highest} (red) · Lowest: {lowest} (blue) · in {last_year}"
)
st.plotly_chart(fig, use_container_width=True)

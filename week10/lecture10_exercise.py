import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from pathlib import Path

st.set_page_config(page_title="CO2 Dashboard", page_icon="🌱", layout="wide")

# ── Data ──────────────────────────────────────────────────────────────────────
# @st.cache_data: Streamlit reruns the entire script on every widget interaction.
# Without caching, the CSV is read from disk on every interaction — slow and wasteful.
# cache_data stores the result after the first run and reuses it until the file changes.
@st.cache_data
def load_data():
    path = Path(__file__).parent.parent / 'data' / 'co2_emissions.csv'
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-01-01')
    return df

df = load_data()

st.title("🌱 CO2 Emissions Explorer")
st.caption("Source: Our World in Data — ourworldindata.org/co2-emissions")

# ── TASK 1: Sidebar with 5 widgets ────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    # a) Selectbox for Region (with 'All')
    regions = ['All'] + sorted(df['Region'].unique().tolist())
    selected_region = st.selectbox("Region", regions)

    # b) Multiselect for Countries — chained to Region
    if selected_region == 'All':
        country_options = sorted(df['Country'].unique().tolist())
    else:
        country_options = sorted(
            df[df['Region'] == selected_region]['Country'].unique().tolist()
        )
    selected_countries = st.multiselect(
        "Countries",
        options=country_options,
        default=country_options[:4]
    )

    # c) date_input for date range — two-handle; years stored as Jan-1 dates
    min_date = datetime.date(int(df['Year'].min()), 1, 1)
    max_date = datetime.date(int(df['Year'].max()), 1, 1)
    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="YYYY-MM-DD"
    )

    st.divider()

    # d) Radio for Metric
    metric = st.radio("Metric", ["Total CO2 (Mt)", "CO2 per capita"])

    # e) Checkbox for highlight mode
    highlight_top = st.checkbox("Show only top emitter highlighted")

# ── Guards ────────────────────────────────────────────────────────────────────
if not selected_countries:
    st.warning("👆 Select at least one country in the sidebar.")
    st.stop()

if len(date_range) != 2:
    st.warning("👆 Select both a start and end date.")
    st.stop()

# Convert date_input result to pd.Timestamp before filtering
start_ts = pd.Timestamp(date_range[0])
end_ts   = pd.Timestamp(date_range[1])

# ── Filter ────────────────────────────────────────────────────────────────────
filtered = df[
    df['Country'].isin(selected_countries) &
    (df['Date'] >= start_ts) &
    (df['Date'] <= end_ts)
].copy()

if filtered.empty:
    st.warning("No data matches the current filters.")
    st.stop()

y_col   = 'CO2_Mt' if metric == "Total CO2 (Mt)" else 'CO2_per_capita'
y_label = 'CO2 Emissions (Mt)' if y_col == 'CO2_Mt' else 'CO2 per Capita (t)'

# ── TASK 2: Filter summary caption ────────────────────────────────────────────
# BBD: always show users how many records match current filters
st.caption(
    f"{len(selected_countries)} countries | "
    f"{selected_region} | "
    f"{date_range[0].strftime('%d %b %Y')} – {date_range[1].strftime('%d %b %Y')} | "
    f"{metric}"
)

# ── EXTENSION: KPI row ────────────────────────────────────────────────────────
last_year  = int(filtered['Year'].max())
first_year = int(filtered['Year'].min())

last_df  = filtered[filtered['Year'] == last_year]
first_df = filtered[filtered['Year'] == first_year]

total_last  = last_df[y_col].sum()
total_first = first_df[y_col].sum()
pct_change  = ((total_last - total_first) / total_first * 100) if total_first != 0 else 0

top_country = last_df.loc[last_df[y_col].idxmax(), 'Country']

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(
    label=f"Total {metric} ({last_year})",
    value=f"{total_last:,.1f}"
)
kpi2.metric(
    label=f"Change ({first_year} → {last_year})",
    value=f"{pct_change:+.1f}%"
)
kpi3.metric(
    label=f"Top Emitter ({last_year})",
    value=top_country
)

st.divider()

# ── TASK 3: Two charts ────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

# ── LEFT: Line chart ──────────────────────────────────────────────────────────
with col_left:
    if highlight_top:
        # SWD grey-and-highlight: identify top emitter over full date range
        total_by_country = (
            filtered.groupby('Country')[y_col].sum().reset_index()
        )
        top_emitter = total_by_country.loc[total_by_country[y_col].idxmax(), 'Country']

        # Build figure manually so we can control per-trace color
        # Color type: categorical (single highlight color vs. grey for all others)
        fig_line = go.Figure()
        for country in selected_countries:
            cdf = filtered[filtered['Country'] == country]
            is_top = country == top_emitter
            fig_line.add_trace(go.Scatter(
                x=cdf['Date'],
                y=cdf[y_col],
                mode='lines',
                name=country,
                line=dict(
                    color='#2E75B6' if is_top else '#D3D3D3',
                    width=3 if is_top else 1.2
                ),
                showlegend=True
            ))
            # Annotate the top emitter at the end of its line
            if is_top and not cdf.empty:
                last_row = cdf[cdf['Date'] == cdf['Date'].max()].iloc[0]
                fig_line.add_annotation(
                    x=last_row['Date'],
                    y=last_row[y_col],
                    text=f"<b>{top_emitter}</b>",
                    showarrow=False,
                    xanchor='left',
                    xshift=6,
                    font=dict(color='#2E75B6', size=11)
                )
        title_text = (
            f"Top emitter ({top_emitter}) dominates — others remain in the background"
        )
    else:
        # Color type: categorical (one distinct color per country via Plotly default palette)
        fig_line = px.line(
            filtered,
            x='Date',
            y=y_col,
            color='Country',
            labels={y_col: y_label, 'Date': ''},
        )
        title_text = f"{metric} over time — {first_year}–{last_year}"

    fig_line.update_layout(
        title=title_text,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial'),
        yaxis_title=y_label,
        xaxis_title='',
        legend=dict(orientation='h', y=-0.2),
        margin=dict(t=60, r=80)
    )
    fig_line.update_xaxes(showgrid=False)
    fig_line.update_yaxes(gridcolor='#EFEFEF')
    st.plotly_chart(fig_line, use_container_width=True)

# ── RIGHT: Bar chart — ranking for last year in selected range ────────────────
with col_right:
    latest = (
        filtered[filtered['Year'] == last_year]
        .sort_values(y_col, ascending=True)
    )
    # Color type: single color (highlight/emphasis — one metric, no category distinction needed)
    fig_bar = px.bar(
        latest,
        x=y_col,
        y='Country',
        orientation='h',
        color_discrete_sequence=['#2E75B6'],
        labels={y_col: y_label, 'Country': ''},
        title=f"Ranking in {last_year}"
    )
    fig_bar.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial'),
        xaxis=dict(range=[0, latest[y_col].max() * 1.15], title=y_label),
        margin=dict(t=60, l=10)
    )
    fig_bar.update_traces(marker_line_width=0)
    fig_bar.update_xaxes(showgrid=False)
    fig_bar.update_yaxes(gridcolor='#EFEFEF')
    st.plotly_chart(fig_bar, use_container_width=True)

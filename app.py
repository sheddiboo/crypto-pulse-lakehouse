import streamlit as st
import awswrangler as wr
import pandas as pd
import plotly.express as px

# ==========================================
# Page Configuration & CSS
# ==========================================
# Configures the default layout to utilize the full width of the screen.
st.set_page_config(page_title="Crypto Market Pulse", page_icon="📈", layout="wide")

# Injects custom CSS to refine the dashboard's visual hierarchy and maximize screen real estate.
st.markdown("""
    <style>
    /* Reduces the default top padding of the Streamlit container */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 0rem;
    }
    /* Enlarges and colors the primary metric values (e.g., Price and Market Cap) */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #00f2ff;
    }
    /* Aligns the section header cleanly with the adjacent metric cards */
    .inline-header {
        margin-top: 0.5rem;
        font-weight: 600;
        font-size: 1.6rem;
    }
    /* Eliminates default margins on subheaders for a tighter UI layout */
    h3 {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Renders the main dashboard title using HTML to ensure precise centering.
st.markdown("<h1 style='text-align: center;'>Crypto Market Pulse Dashboard</h1>", unsafe_allow_html=True)

# ==========================================
# Data Connection
# ==========================================
# Caches the Athena query results for 5 minutes (300 seconds) to reduce AWS costs and improve latency.
@st.cache_data(ttl=300)
def load_data():
    """Fetches the transformed Gold layer data directly from AWS Athena."""
    query = "SELECT * FROM fct_crypto_market_pulse ORDER BY observed_at DESC"
    df = wr.athena.read_sql_query(sql=query, database="crypto_pulse_db", ctas_approach=False)
    # Converts the string timestamp into a pandas datetime object for Plotly compatibility.
    df['observed_at'] = pd.to_datetime(df['observed_at'])
    return df

# Displays a loading spinner while the dashboard syncs with the data lake.
with st.spinner("Synchronizing with Lakehouse..."):
    try:
        df = load_data()
    except Exception as e:
        # Halts the application gracefully if the database connection fails.
        st.error(f"Connection Error: {e}")
        st.stop()

# ==========================================
# Global Controls
# ==========================================
# Extracts the most recent timestamp to inform the user of data freshness.
latest_time_wat = df['observed_at'].max()
str_wat = latest_time_wat.strftime('%Y-%m-%d %I:%M %p WAT')
st.caption(f"Last Pipeline Sync: {str_wat}")

# Generates an alphabetical list of unique assets available in the database.
coins = list(sorted(df['coin_id'].unique()))

# Identifies the index position of Bitcoin to set it as the default selection on initial load.
default_idx = coins.index('bitcoin') if 'bitcoin' in coins else 0

# Restricts the width of the dropdown menu to the top-left corner to prevent it from spanning the entire screen.
select_col, empty_space = st.columns([1, 4]) 
with select_col:
    selected_coin = st.selectbox("Select Asset to Analyze", coins, index=default_idx, label_visibility="collapsed")

# ==========================================
# Temporal Trends & Asset Detail
# ==========================================
# Filters the dataset for the selected asset and isolates the most recent data point for the metric cards.
coin_history = df[df['coin_id'] == selected_coin].sort_values('observed_at')
current_asset = coin_history.iloc[-1] 

# Structures the layout into three columns: a wide column for the title, and two narrower columns for the metrics.
head_col, met_col1, met_col2 = st.columns([4, 2, 3])

with head_col:
    st.markdown(f'<p class="inline-header">{selected_coin.capitalize()} 7-Day Performance</p>', unsafe_allow_html=True)
    
with met_col1:
    st.metric(
        label=f"Current Price", 
        value=f"${current_asset['price']:,.2f}",
        delta=f"{current_asset['pct_change_24h']:.2f}% (24h)"
    )
    
with met_col2:
    # Extracts the market cap safely, defaulting to 0 if the data is unavailable.
    mkt_cap = current_asset.get('market_cap', 0)
    st.metric(
        label="Total Market Cap", 
        value=f"${mkt_cap:,.0f}" if mkt_cap > 0 else "N/A"
    )

# Constructs a dual-line time series chart mapping actual price against the 24-hour moving average.
fig_line = px.line(
    coin_history,
    x='observed_at',
    y=['price', 'moving_avg_24h'],
    labels={'value': 'USD', 'observed_at': '', 'variable': 'Metric'}, 
    color_discrete_map={'price': '#00f2ff', 'moving_avg_24h': '#ffaa00'},
    height=450,
    template="plotly_dark"
)

# Refines the chart layout by repositioning the legend and removing the x-axis title.
fig_line.update_layout(
    margin=dict(l=0, r=0, t=10, b=0), 
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_title=None 
)
# config={'displayModeBar': False} removes the zoom/pan/export toolbar.
st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# Dynamic Market Composition 
# ==========================================
st.subheader("Market Composition Analysis")

# Isolates the most recent row for every coin to calculate current market composition.
metric_col = 'market_cap'
latest_all = df.sort_values('observed_at').groupby('coin_id').tail(1)

# Aggregates the market cap of the currently selected asset versus the sum of all other available assets.
selected_val = latest_all[latest_all['coin_id'] == selected_coin][metric_col].sum()
others_val = latest_all[latest_all['coin_id'] != selected_coin][metric_col].sum()

pie_df = pd.DataFrame({
    'Category': [selected_coin.capitalize(), 'Others Combined'],
    'Value': [selected_val, others_val]
})

# Prepares the dataframe for the bar chart comparison.
bar_df = latest_all.sort_values(metric_col, ascending=False).copy()
# Converts raw market cap values into billions for cleaner visual labeling.
bar_df['market_cap_billions'] = bar_df[metric_col] / 1e9
# Assigns a specific group label to highlight the selected asset dynamically.
bar_df['ColorGroup'] = bar_df['coin_id'].apply(lambda x: selected_coin.capitalize() if x == selected_coin else 'Other Assets')

# Defines a consistent color palette: highlight color for the selected asset, muted color for the rest.
color_map = {
    selected_coin.capitalize(): '#ffaa00', 
    'Others Combined': '#1f77b4',
    'Other Assets': '#1f77b4'
}

# Splits the bottom layout into two equal-width columns.
c1, c2 = st.columns(2)

with c1:
    # Renders a donut chart illustrating the market dominance of the selected asset.
    fig_pie = px.pie(
        pie_df, values='Value', names='Category', 
        title=f"{selected_coin.capitalize()} vs Others (Market Cap)",
        hole=0.4, 
        color='Category',
        color_discrete_map=color_map,
        height=550 
    )
    # Tightens the chart margins to align perfectly with the adjacent bar chart.
    fig_pie.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

with c2:
    # Renders a bar chart comparing the market cap of all available assets.
    fig_bar = px.bar(
        bar_df, x='coin_id', y='market_cap_billions', color='ColorGroup',
        title="Market Cap Comparison",
        labels={'market_cap_billions': '', 'coin_id': ''}, 
        color_discrete_map=color_map,
        text='market_cap_billions', 
        height=550, 
        template="plotly_dark"
    )
    
    # Places the formatted billion-dollar values directly on top of the bars and prevents them from being cropped.
    fig_bar.update_traces(
        texttemplate='%{text:,.1f}B', 
        textposition='outside',
        cliponaxis=False
    )
    
    # Achieves a minimalist aesthetic by completely hiding the Y-axis, gridlines, and X-axis title.
    fig_bar.update_yaxes(visible=False, showgrid=False)
    fig_bar.update_xaxes(title=None)
    
    fig_bar.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
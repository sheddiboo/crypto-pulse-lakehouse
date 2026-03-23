import streamlit as st
import awswrangler as wr
import pandas as pd
import plotly.express as px

# ==========================================
# Page Configuration & CSS
# ==========================================
st.set_page_config(page_title="Crypto Market Pulse", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 0rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #00f2ff;
    }
    .inline-header {
        margin-top: 0.5rem;
        font-weight: 600;
        font-size: 1.6rem;
    }
    /* Tighter spacing for section headers */
    h3 {
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Crypto Market Pulse Dashboard</h1>", unsafe_allow_html=True)

# ==========================================
# Data Connection
# ==========================================
@st.cache_data(ttl=300)
def load_data():
    query = "SELECT * FROM fct_crypto_market_pulse ORDER BY observed_at DESC"
    df = wr.athena.read_sql_query(sql=query, database="crypto_pulse_db", ctas_approach=False)
    df['observed_at'] = pd.to_datetime(df['observed_at'])
    return df

with st.spinner("Synchronizing with Lakehouse..."):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

# ==========================================
# Global Controls
# ==========================================
latest_time_wat = df['observed_at'].max()
str_wat = latest_time_wat.strftime('%Y-%m-%d %I:%M %p WAT')
st.caption(f"Last Pipeline Sync: {str_wat}")

coins = list(sorted(df['coin_id'].unique()))

# --- Set Bitcoin as Default ---
default_idx = coins.index('bitcoin') if 'bitcoin' in coins else 0

select_col, empty_space = st.columns([1, 4]) 
with select_col:
    selected_coin = st.selectbox("Select Asset to Analyze", coins, index=default_idx, label_visibility="collapsed")

# ==========================================
# Temporal Trends & Asset Detail
# ==========================================
coin_history = df[df['coin_id'] == selected_coin].sort_values('observed_at')
current_asset = coin_history.iloc[-1] 

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
    mkt_cap = current_asset.get('market_cap', 0)
    st.metric(
        label="Total Market Cap", 
        value=f"${mkt_cap:,.0f}" if mkt_cap > 0 else "N/A"
    )

fig_line = px.line(
    coin_history,
    x='observed_at',
    y=['price', 'moving_avg_24h'],
    labels={'value': 'USD', 'observed_at': '', 'variable': 'Metric'}, 
    color_discrete_map={'price': '#00f2ff', 'moving_avg_24h': '#ffaa00'},
    height=450,
    template="plotly_dark"
)

fig_line.update_layout(
    margin=dict(l=0, r=0, t=10, b=0), 
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_title=None 
)
st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# Dynamic Market Composition 
# ==========================================
st.subheader("Market Composition Analysis")

metric_col = 'market_cap'
latest_all = df.sort_values('observed_at').groupby('coin_id').tail(1)

# Pie Chart Logic
selected_val = latest_all[latest_all['coin_id'] == selected_coin][metric_col].sum()
others_val = latest_all[latest_all['coin_id'] != selected_coin][metric_col].sum()

pie_df = pd.DataFrame({
    'Category': [selected_coin.capitalize(), 'Others Combined'],
    'Value': [selected_val, others_val]
})

# --- Bar Chart Billions Logic ---
bar_df = latest_all.sort_values(metric_col, ascending=False).copy()
# Force Market Cap into Billions
bar_df['market_cap_billions'] = bar_df[metric_col] / 1e9
bar_df['ColorGroup'] = bar_df['coin_id'].apply(lambda x: selected_coin.capitalize() if x == selected_coin else 'Other Assets')

color_map = {
    selected_coin.capitalize(): '#ffaa00', 
    'Others Combined': '#1f77b4',
    'Other Assets': '#1f77b4'
}

c1, c2 = st.columns(2)

with c1:
    fig_pie = px.pie(
        pie_df, values='Value', names='Category', 
        title=f"{selected_coin.capitalize()} vs Others (Market Cap)",
        hole=0.4, 
        color='Category',
        color_discrete_map=color_map,
        height=550 
    )
    # Tighter margins to match the layout
    fig_pie.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    fig_bar = px.bar(
        bar_df, x='coin_id', y='market_cap_billions', color='ColorGroup',
        title="Market Cap Comparison",
        labels={'market_cap_billions': '', 'coin_id': ''}, # Removed axis labels
        color_discrete_map=color_map,
        text='market_cap_billions', 
        height=550, 
        template="plotly_dark"
    )
    
    # Format text and prevent clipping
    fig_bar.update_traces(
        texttemplate='%{text:,.1f}B', 
        textposition='outside',
        cliponaxis=False
    )
    
    # THE CLEANUP: Hide the Y-axis completely and remove the X-axis title space
    fig_bar.update_yaxes(visible=False, showgrid=False)
    fig_bar.update_xaxes(title=None)
    
    fig_bar.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig_bar, use_container_width=True)
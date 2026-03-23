import streamlit as st
import awswrangler as wr
import pandas as pd
import plotly.express as px

# ==========================================
# Page Configuration & Custom CSS
# ==========================================
st.set_page_config(page_title="Crypto Market Pulse", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    /* Center and resize the main title */
    .main-title {
        text-align: center;
        font-size: 2.2rem; /* Reduced from default */
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    /* Reduce subtitle sizes */
    .custom-subheader {
        font-size: 1.3rem; /* Reduced size */
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 0rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        color: #00f2ff;
    }
    </style>
""", unsafe_allow_html=True)

# Centered Title
st.markdown('<p class="main-title">Crypto Market Pulse Dashboard</p>', unsafe_allow_html=True)

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
# Temporal Trends & Asset Detail
# ==========================================
latest_time_wat = df['observed_at'].max()
str_wat = latest_time_wat.strftime('%Y-%m-%d %I:%M %p WAT')
st.caption(f"Last Pipeline Sync: {str_wat}")

@st.fragment
def render_main_section(data):
    # Asset Selection
    coins = sorted(data['coin_id'].unique())
    selected_coin = st.selectbox("Select Asset to Analyze", coins)
    
    coin_history = data[data['coin_id'] == selected_coin].sort_values('observed_at')
    current_asset = coin_history.iloc[0] 
    
    # Detail Cards
    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        st.metric(
            label=f"Current {selected_coin.capitalize()} Price", 
            value=f"${current_asset['price']:,.2f}",
            delta=f"{current_asset['pct_change_24h']:.2f}% (24h)"
        )
    with col2:
        mkt_cap = current_asset.get('market_cap', 0)
        st.metric(
            label="Total Market Cap", 
            value=f"${mkt_cap:,.0f}" if mkt_cap > 0 else "N/A"
        )
        
    st.markdown(f'<p class="custom-subheader">{selected_coin.capitalize()} 7-Day Performance</p>', unsafe_allow_html=True)
    
    fig = px.line(
        coin_history,
        x='observed_at',
        y=['price', 'moving_avg_24h'],
        labels={'value': 'USD', 'observed_at': 'Time (WAT)', 'variable': 'Metric'},
        color_discrete_map={'price': '#00f2ff', 'moving_avg_24h': '#ffaa00'},
        height=450,
        template="plotly_dark"
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

render_main_section(df)

st.divider()

# ==========================================
# Market Composition (Market Cap Only)
# ==========================================
st.markdown('<p class="custom-subheader">Market Composition Analysis</p>', unsafe_allow_html=True)

# Lock metric to Market Cap
metric_col = 'market_cap'
latest_all = df.sort_values('observed_at').groupby('coin_id').tail(1)

# Logic for Pie Chart
btc_val = latest_all[latest_all['coin_id'] == 'bitcoin'][metric_col].sum()
others_val = latest_all[latest_all['coin_id'] != 'bitcoin'][metric_col].sum()

pie_df = pd.DataFrame({
    'Category': ['Bitcoin', 'Others Combined'],
    'Value': [btc_val, others_val]
})

# Logic for Bar Chart (Others only)
others_df = latest_all[latest_all['coin_id'] != 'bitcoin'].sort_values(metric_col, ascending=False)

c1, c2 = st.columns(2)

with c1:
    fig_pie = px.pie(
        pie_df, values='Value', names='Category', 
        title="Bitcoin vs Others (Market Cap Ratio)",
        hole=0.4, color_discrete_sequence=['#ffaa00', '#00f2ff']
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    fig_bar = px.bar(
        others_df, x='coin_id', y=metric_col, color='coin_id',
        title="Market Cap Comparison (Excluding Bitcoin)",
        labels={metric_col: 'Market Cap (USD)', 'coin_id': 'Asset'},
        template="plotly_dark"
    )
    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)
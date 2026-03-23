import streamlit as st
import awswrangler as wr
import pandas as pd
import plotly.express as px

# ==========================================
# Page Configuration & CSS Styling
# ==========================================
st.set_page_config(page_title="Crypto Market Pulse", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Crypto Market Pulse Dashboard")

# ==========================================
# Data Connection
# ==========================================
@st.cache_data(ttl=300) # Reduced TTL to 5 mins to catch the :20 updates faster
def load_data():
    query = """
        SELECT * FROM fct_crypto_market_pulse 
        ORDER BY observed_at DESC
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database="crypto_pulse_db",
        ctas_approach=False 
    )
    df['observed_at'] = pd.to_datetime(df['observed_at'])
    return df

with st.spinner("Fetching Pre-Optimized Gold Layer data from AWS Athena..."):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"Error connecting to Athena: {e}")
        st.stop()

# ==========================================
# Header & Metric Carousel
# ==========================================
latest_time_wat = df['observed_at'].max()
str_wat = latest_time_wat.strftime('%Y-%m-%d %I:%M %p WAT')

st.subheader(f"📊 Current Market Snapshot (As of {str_wat})")

if 'metric_page' not in st.session_state:
    st.session_state.metric_page = 0

latest_df = df[df['observed_at'] == latest_time_wat].reset_index(drop=True)

items_per_page = 5
total_items = len(latest_df)
total_pages = (total_items - 1) // items_per_page + 1

def prev_page():
    if st.session_state.metric_page > 0:
        st.session_state.metric_page -= 1

def next_page():
    if st.session_state.metric_page < total_pages - 1:
        st.session_state.metric_page += 1

cols = st.columns([0.5, 2, 2, 2, 2, 2, 0.5])

with cols[0]:
    if st.session_state.metric_page > 0:
        st.button("◀", on_click=prev_page, key="prev_btn", use_container_width=True)

start_idx = st.session_state.metric_page * items_per_page
end_idx = start_idx + items_per_page
current_page_df = latest_df.iloc[start_idx:end_idx]

for i, (idx, row) in enumerate(current_page_df.iterrows()):
    with cols[i + 1]:
        st.metric(
            label=row['coin_id'].capitalize(),
            value=f"${row['price']:,.2f}",
            delta=f"{row['pct_change_24h']:.2f}%"
        )

with cols[6]:
    if st.session_state.metric_page < total_pages - 1:
        st.button("▶", on_click=next_page, key="next_btn", use_container_width=True)

st.divider()

# ==========================================
# NEW: Categorical Distribution (Project Requirement)
# ==========================================
st.subheader("🏗️ Market Composition (Categorical Distribution)")

# Get the latest price for every unique coin to compare them
latest_all_coins = df.sort_values('observed_at').groupby('coin_id').tail(1)

fig_dist = px.bar(
    latest_all_coins,
    x='coin_id',
    y='price',
    color='coin_id',
    title="Price Distribution Across Asset Categories",
    labels={'price': 'Current Price (USD)', 'coin_id': 'Cryptocurrency'},
    text_auto='.2s',
    template="plotly_dark"
)
fig_dist.update_layout(showlegend=False, height=450, margin=dict(t=40, b=0))
st.plotly_chart(fig_dist, use_container_width=True)

st.divider()

# ==========================================
# Temporal Trends
# ==========================================
st.subheader("📉 7-Day Price Trends & Moving Averages")

@st.fragment
def render_interactive_chart(data):
    selected_coin = st.selectbox("Select an Asset to View", data['coin_id'].unique(), label_visibility="collapsed")
    coin_data = data[data['coin_id'] == selected_coin].sort_values('observed_at')

    fig = px.line(
        coin_data,
        x='observed_at',
        y=['price', 'moving_avg_24h'],
        labels={'value': 'Price (USD)', 'observed_at': 'Time (WAT)', 'variable': 'Metric'},
        color_discrete_map={'price': '#1f77b4', 'moving_avg_24h': '#ff7f0e'},
        height=600 
    )

    newnames = {'price': 'Actual Price', 'moving_avg_24h': '24h Moving Average'}
    fig.for_each_trace(lambda t: t.update(
        name=newnames[t.name],
        legendgroup=newnames[t.name],
        hovertemplate=t.hovertemplate.replace(t.name, newnames[t.name])
    ))
    
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

render_interactive_chart(df)
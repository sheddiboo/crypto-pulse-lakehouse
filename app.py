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
        font-size: 1.6rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Crypto Market Pulse Dashboard")

# ==========================================
# Data Connection
# ==========================================
@st.cache_data(ttl=300)
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

with st.spinner("Fetching data from AWS Athena..."):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"Error connecting to Athena: {e}")
        st.stop()

# ==========================================
# Current Market Snapshot (All 10 Coins)
# ==========================================
latest_time_wat = df['observed_at'].max()
str_wat = latest_time_wat.strftime('%Y-%m-%d %I:%M %p WAT')

st.subheader(f"Current Market Snapshot (As of {str_wat})")

# Filter for the most recent data
latest_df = df[df['observed_at'] == latest_time_wat].sort_values('coin_id').reset_index(drop=True)

# Display all 10 coins in two rows of 5
row1 = latest_df.iloc[0:5]
row2 = latest_df.iloc[5:10]

cols1 = st.columns(5)
for i, (idx, row) in enumerate(row1.iterrows()):
    with cols1[i]:
        st.metric(label=row['coin_id'].capitalize(), value=f"${row['price']:,.2f}", delta=f"{row['pct_change_24h']:.2f}%")

cols2 = st.columns(5)
for i, (idx, row) in enumerate(row2.iterrows()):
    with cols2[i]:
        st.metric(label=row['coin_id'].capitalize(), value=f"${row['price']:,.2f}", delta=f"{row['pct_change_24h']:.2f}%")

st.divider()

# ==========================================
# Market Composition (Categorical Distribution)
# ==========================================
st.subheader("Market Composition (Categorical Distribution)")

latest_all_coins = df.sort_values('observed_at').groupby('coin_id').tail(1)

# Prepare Data for Pie Chart (Bitcoin vs Others)
btc_price = latest_all_coins[latest_all_coins['coin_id'] == 'bitcoin']['price'].sum()
others_price = latest_all_coins[latest_all_coins['coin_id'] != 'bitcoin']['price'].sum()
pie_data = pd.DataFrame({
    'Asset Group': ['Bitcoin', 'All Others Combined'],
    'Total Price Value': [btc_price, others_price]
})

# Prepare Data for Bar Chart (Others Only)
others_df = latest_all_coins[latest_all_coins['coin_id'] != 'bitcoin'].sort_values('price', ascending=False)

col_pie, col_bar = st.columns(2)

with col_pie:
    fig_pie = px.pie(
        pie_data, 
        values='Total Price Value', 
        names='Asset Group', 
        title="Bitcoin vs Others (Price Ratio)",
        color_discrete_sequence=['#00CC96', '#636EFA']
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    fig_bar = px.bar(
        others_df, 
        x='coin_id', 
        y='price', 
        color='coin_id', 
        title="Price Comparison (Excluding Bitcoin)",
        labels={'price': 'Price (USD)', 'coin_id': 'Cryptocurrency'},
        template="plotly_dark"
    )
    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ==========================================
# Temporal Trends
# ==========================================
st.subheader("7-Day Price Trends and Moving Averages")

@st.fragment
def render_interactive_chart(data):
    selected_coin = st.selectbox("Select an Asset", data['coin_id'].unique(), label_visibility="collapsed")
    coin_data = data[data['coin_id'] == selected_coin].sort_values('observed_at')

    fig = px.line(
        coin_data,
        x='observed_at',
        y=['price', 'moving_avg_24h'],
        labels={'value': 'Price (USD)', 'observed_at': 'Time (WAT)', 'variable': 'Metric'},
        color_discrete_map={'price': '#1f77b4', 'moving_avg_24h': '#ff7f0e'},
        height=500 
    )
    
    # Clean up legend names
    newnames = {'price': 'Actual Price', 'moving_avg_24h': '24h Moving Average'}
    fig.for_each_trace(lambda t: t.update(name=newnames[t.name]))
    
    st.plotly_chart(fig, use_container_width=True)

render_interactive_chart(df)
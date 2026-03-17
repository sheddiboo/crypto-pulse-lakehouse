import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from tqdm import tqdm

# Setup and Authentication
# Loads environment variables to securely access the API key.
load_dotenv()
API_KEY = os.getenv('api_key')

if not API_KEY:
    raise ValueError("API Key not found. Please verify the .env file configuration.")

HEADERS = {"x-cg-demo-api-key": API_KEY}
COINS = [
    'bitcoin', 'ethereum', 'tether', 'ripple', 'binancecoin', 
    'usd-coin', 'solana', 'tron', 'dogecoin', 'hyperliquid'
]

# Data Fetching Logic
def fetch_chunk(coin_id, start_ts, end_ts):
    """Fetches a specific time window of historical data for a designated coin."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    params = {'vs_currency': 'usd', 'from': start_ts, 'to': end_ts}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {coin_id}: {e}")
        return None

# Main Execution Flow
def run_backfill():
    end_date = datetime.now(timezone.utc)
    
    # Defines time windows to chunk the historical data retrieval.
    # The API requires ranges under ninety days to return hourly granularity.
    chunks = [
        (90, 0),     
        (180, 90),   
        (270, 180),  
        (365, 270)   
    ]

    print("🚀 Starting Historical Backfill (Per Coin)...")
    
    # Ensures the output directory exists within the project root.
    os.makedirs("data", exist_ok=True)
    
    # Initializes a progress bar for the terminal execution.
    for coin in tqdm(COINS, desc="Processing Coins"):
        
        # Initializes an empty list to store records for the current coin iteration.
        coin_records = []
        
        for start_offset, end_offset in chunks:
            # Calculates the exact Unix timestamps for the current chunk window.
            chunk_start = int((end_date - timedelta(days=start_offset)).timestamp())
            chunk_end = int((end_date - timedelta(days=end_offset)).timestamp())
            
            data = fetch_chunk(coin, chunk_start, chunk_end)
            
            if data:
                prices = data.get('prices', [])
                market_caps = data.get('market_caps', [])
                
                # Creates a dictionary for efficient lookup of market caps by timestamp.
                mcap_dict = {item[0]: item[1] for item in market_caps}
                
                for item in prices:
                    timestamp_ms = item[0]
                    coin_records.append({
                        'coin_id': coin,
                        'timestamp': datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc),
                        'price_usd': item[1],
                        'market_cap': mcap_dict.get(timestamp_ms)
                    })
            
            # Enforces a delay between API calls to respect rate limits.
            time.sleep(3)

        # Processing and Storage
        if coin_records:
            df = pd.DataFrame(coin_records)
            
            # Drops duplicate timestamps and sorts the dataset chronologically.
            df = df.drop_duplicates(subset=['timestamp'])
            df = df.sort_values(by=['timestamp']).reset_index(drop=True)
            
            # Saves the structured data as a compressed Parquet file for the specific coin.
            output_path = f"data/{coin}_historical_1yr.parquet"
            df.to_parquet(output_path, engine='pyarrow', index=False)

    print(f"\n✅ Success! All Parquet files have been saved to the 'data/' folder.")

if __name__ == "__main__":
    run_backfill()
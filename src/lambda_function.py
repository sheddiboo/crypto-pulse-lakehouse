import os
import requests
import boto3
from datetime import datetime
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def lambda_handler(event, context):
    api_key = os.environ.get('COINGECKO_API_KEY', '').strip()
    bucket_name = os.environ.get('RAW_S3_BUCKET')
    
    if not api_key:
        logger.error("Environment variable COINGECKO_API_KEY is empty or missing")
        raise Exception("COINGECKO_API_KEY is not set")

    coins = ['bitcoin', 'ethereum', 'solana', 'binancecoin', 'ripple', 
             'dogecoin', 'tether', 'tron', 'usd-coin', 'hyperliquid']
    
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': ','.join(coins),
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true',
        'include_last_updated_at': 'true',
        'x_cg_demo_api_key': api_key  
    }
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-cg-demo-api-key": api_key 
    }

    logger.info(f"Requesting data for {len(coins)} coins.")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"API Error {response.status_code}: {response.text}")
            response.raise_for_status()

        raw_data = response.json()
        
        # Flatten the JSON dictionary into a list of row records
        flattened_data = []
        for coin_id, metrics in raw_data.items():
            row = {
                "coin_id": coin_id,
                "price": float(metrics.get("usd", 0)),
                "market_cap": float(metrics.get("usd_market_cap", 0)),
                "total_volume": float(metrics.get("usd_24h_vol", 0)),
                "timestamp": int(metrics.get("last_updated_at", 0))
            }
            flattened_data.append(row)

        # Convert the records to a PyArrow Table via a Pandas DataFrame
        df = pd.DataFrame(flattened_data)
        table = pa.Table.from_pandas(df)
        
        # Write the PyArrow Table to an in-memory buffer as a Parquet file
        parquet_buffer = BytesIO()
        pq.write_table(table, parquet_buffer)
        
        # Define the S3 file path with time partitions and a .parquet extension
        now = datetime.now()
        timestamp_path = now.strftime("%Y/%m/%d/%H")
        file_name = f"hourly_ingestion/{timestamp_path}/crypto_data_{now.strftime('%M%S')}.parquet"
        
        # Upload the in-memory Parquet buffer directly to the S3 bucket
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=parquet_buffer.getvalue()
        )
        
        logger.info(f"Successfully saved Parquet file to S3: {file_name}")
        
        return {
            'statusCode': 200,
            'body': f"Success! Saved {file_name}"
        }

    except Exception as e:
        logger.error(f"Critical Failure: {str(e)}")
        raise e

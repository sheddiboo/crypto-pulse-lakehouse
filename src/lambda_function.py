import os
import json
import boto3
import requests
from datetime import datetime

# Initializes the AWS S3 client
s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Retrieves target assets and infrastructure configuration from the environment
    COINS = ["bitcoin", "ethereum", "solana", "cardano", "polkadot", 
             "ripple", "dogecoin", "chainlink", "staked-ether", "binancecoin"]
    BUCKET = os.environ.get('RAW_S3_BUCKET')
    API_KEY = os.environ.get('COINGECKO_API_KEY')
    
    # Initializes an empty list to store the extracted data points
    all_data = []
    
    # Iterates through the target coins to fetch the latest 24 hours of market data
    for coin in COINS:
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': '1',
            'interval': 'hourly',
            'api_key': API_KEY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        # Formats the raw response payload to match the target schema
        if 'prices' in data:
            for i in range(len(data['prices'])):
                all_data.append({
                    'coin_id': coin,
                    'timestamp_ms': data['prices'][i][0],
                    'price': data['prices'][i][1],
                    'market_cap': data['market_caps'][i][1] if i < len(data['market_caps']) else None,
                    'ingested_at': datetime.utcnow().isoformat()
                })

    # Generates a dynamic file path partitioned by the current UTC execution time
    file_name = f"hourly_ingestion/{datetime.utcnow().strftime('%Y/%m/%d/%H')}_batch.json"
    
    # Uploads the formatted JSON batch directly to the designated S3 zone
    s3.put_object(
        Bucket=BUCKET,
        Key=file_name,
        Body=json.dumps(all_data),
        ContentType='application/json'
    )
    
    # Returns a standard execution summary to the Lambda logs
    return {
        'statusCode': 200,
        'body': json.dumps(f"Successfully ingested {len(all_data)} records to {file_name}")
    }
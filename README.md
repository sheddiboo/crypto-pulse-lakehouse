# 📈 Crypto Market Pulse: A Serverless Medallion Lakehouse

## 🎯 Problem Statement
Cryptocurrency markets operate 24/7, making it difficult to maintain a unified, highly accurate dataset that seamlessly bridges deep historical data with live, up-to-the-minute price action. 

This project solves that problem by building a **fully automated, serverless Medallion Data Lakehouse**. It ingests a year of historical backfill data and seamlessly merges it with live hourly updates from the CoinGecko API. The pipeline automatically deduplicates overlapping records, calculates 24-hour moving averages, and serves the optimized data to an interactive Streamlit dashboard.

---

## 🛠️ Technology Stack 
While the course heavily focused on Google Cloud Platform (GCP) and traditional orchestrators (Kestra/Mage/Airflow), I chose to challenge myself by building a **fully Serverless architecture on AWS**. 

Here is how my chosen tools map to the course curriculum:

| Concept | Course Curriculum | My Architecture | Why I Chose It (Tool Explanation) |
| :--- | :--- | :--- | :--- |
| **Cloud Provider** | GCP | **AWS** | Industry standard cloud provider with robust serverless offerings. |
| **Infrastructure as Code** | Terraform | **Terraform** | Used via a Dockerized `Makefile` to ensure zero local dependencies. |
| **Orchestration (Batch)** | Kestra / Airflow | **AWS EventBridge** | A serverless event bus. Instead of paying for an always-on Airflow server, EventBridge triggers my pipeline exactly on the hour using a cron expression. |
| **Data Ingestion** | Python Scripts | **AWS Lambda (Dockerized)** | Serverless compute. A custom Docker image using `uv` runs my Python extraction logic, pulling from the CoinGecko API. |
| **Data Lake Storage** | Google Cloud Storage | **AWS S3** | Used to build a "Bronze" raw zone and a "Gold" optimized zone. |
| **Data Warehouse** | BigQuery | **AWS Athena + Glue** | **Glue Crawler:** Automatically scans my S3 buckets to infer schemas and build a data catalog. <br>**Athena:** A serverless query engine (based on Trino/Presto) that allows me to run standard SQL directly against Parquet files in S3 without loading them into a traditional database. |
| **Transformations** | dbt | **dbt Core (`dbt-athena`)** | Builds the Silver (Staging) and Gold (Marts) layers, handling deduplication and rolling averages. |
| **Dashboard** | Looker Studio | **Streamlit** | Python-based UI connected directly to Athena via `boto3`/`awswrangler`. |

---

## 🏗️ Architecture & Pipeline Flow

1. **The Backfill (One-Off):** A Python script fetches 1 year of historical data from CoinGecko, converts it to Parquet using `pandas` and `pyarrow`, and uploads it to the Bronze S3 bucket.
2. **Live Ingestion (Hourly Batch):** AWS EventBridge fires every hour, triggering a Dockerized AWS Lambda function. The function fetches the latest prices and drops a new Parquet file into the Bronze S3 bucket partitioned by `year/month/day/hour`.
3. **The Data Catalog (Automated):** An AWS Glue Crawler runs on a cron schedule (`15 * * * ? *`), detecting new S3 partitions and automatically updating the AWS Glue Data Catalog.
4. **Transformation (dbt):**
    * **Silver Layer (`stg_crypto_prices`):** A view that unifies historical and live data, standardizes timestamps, and uses `ROW_NUMBER()` window functions to drop duplicate records where the live pipeline overlaps the historical backfill.
    * **Gold Layer (`fct_crypto_market_pulse`):** A materialized Parquet table that calculates the rolling 24-hour moving average and 24-hour percentage change.
5. **Dashboard:** Streamlit queries the Gold table in Athena to visualize the data.

---

## 📊 The Dashboard
The Streamlit dashboard fulfills the project requirement of having at least two distinct tiles:
* **Tile 1 (Temporal):** A time-series line chart visualizing the real-time price trend overlaid with the 24-hour moving average.
* **Tile 2 (Categorical/Metrics):** Dynamic KPI cards comparing the current market cap and 24-hour percentage change across the tracked cryptocurrencies.

---

## 🚀 Reproducibility (How to run this project)

I implemented a **Dockerized Makefile** approach. You do not need to install Terraform locally to deploy this infrastructure.

### Prerequisites
1. Docker installed and running.
2. An AWS Account with configured credentials (`~/.aws/credentials`).
3. A free CoinGecko API Key.

### Step 1: Environment Setup
Clone the repository and create a `.env` file in the root directory:
```bash
COINGECKO_API_KEY="your_api_key_here"
```

### Step 2: Deploy Infrastructure
Use the provided `Makefile` to deploy the AWS architecture via a HashiCorp Docker container:
```bash
make tf-init
make tf-apply
```
*(This creates the S3 buckets, IAM roles, ECR repository, Lambda function, EventBridge rule, and Glue Crawler).*

### Step 3: Deploy Lambda Code
Build and push the Dockerized Python ingestion script to AWS ECR:
```bash
make docker-push
```

### Step 4: Run Transformations
Navigate to the dbt project, ensure your `profiles.yml` points to the newly created S3 Gold bucket, and run the pipeline:
```bash
cd transform
dbt run
```

### Step 5: Launch the Dashboard
Start the Streamlit application locally:
```bash
streamlit run app.py
```

### Teardown
To avoid AWS charges, destroy all infrastructure when finished:
```bash
make tf-destroy
```
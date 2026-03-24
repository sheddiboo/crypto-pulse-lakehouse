# 📈 Crypto Market Pulse: A Serverless Lakehouse

## 🎯 Problem Statement
Cryptocurrency markets operate 24/7, making it difficult to maintain a unified, highly accurate dataset that seamlessly bridges deep historical data with live, up-to-the-minute price action. 

This project solves that problem by building a **fully automated, serverless Medallion Data Lakehouse**. It ingests a year of historical backfill data and seamlessly merges it with live hourly updates from the CoinGecko API. The pipeline automatically deduplicates overlapping records, calculates 24-hour moving averages, tracks market cap dominance, and serves the optimized data to a highly interactive, professional-grade Streamlit dashboard.

---

## 🛠️ Technology Stack & Architecture Design
The Data Engineering curriculum extensively covers fundamental concepts using Google Cloud Platform (GCP) and traditional always-on orchestration tools. For this capstone, I applied those core engineering principles but pivoted to a **fully Serverless architecture on AWS** to challenge myself with event-driven design and minimize idle computing costs.

Here is a deep dive into the architecture and the rationale behind each technology:

### 1. Infrastructure as Code (IaC) & Containerization
* **Terraform:** As taught in the course, manually clicking through cloud consoles is not reproducible or scalable. I used Terraform to declaratively provision all AWS resources (S3, ECR, IAM, Lambda, EventBridge, Glue). To take it a step further, I executed Terraform via a Dockerized `Makefile` to ensure there are zero local dependencies required to deploy the infrastructure.
* **Docker:** Containerization ensures that code runs the same way everywhere. Instead of relying on standard AWS Lambda zip uploads, which have severe size limits, I packaged my Python ingestion scripts inside a Docker image. This allowed me to safely include heavy data-science libraries like `pandas` and `pyarrow`.

### 2. Orchestration (The Serverless Pivot)
* **AWS EventBridge & dbt Cloud:** Traditional orchestration tools taught in the course (like Apache Airflow, Mage, or Kestra) require an always-on server (EC2 or similar compute instance) constantly running to check schedules, which incurs continuous costs. I opted for a serverless approach: 
  * **EventBridge** acts as the cron scheduler, firing exactly on the hour to trigger the Lambda ingestion function. 
  * **dbt Cloud** handles the downstream transformation orchestration, running automatically at 20 minutes past the hour. This decoupled, event-driven approach means I only pay for the exact seconds the code is running.

### 3. Data Lake Storage & Formats
* **AWS S3:** The AWS equivalent to Google Cloud Storage (GCS). It serves as the foundation of the Medallion Lakehouse, divided logically into a "Bronze" raw zone and a "Gold" optimized zone.
* **Parquet:** Instead of storing raw data as CSV or JSON, the ingestion scripts convert the data in-memory to native columnar Parquet files before uploading to S3. This drastically reduces storage size and heavily optimizes the downstream query scanning speed.

### 4. Data Warehouse & Query Engine
* **AWS Athena + AWS Glue:** Instead of loading data into a traditional managed Data Warehouse like BigQuery or Redshift, I utilized a true Lakehouse approach.
  * **AWS Glue Crawler** automatically scans the S3 buckets, infers the schema of the Parquet files, and builds a metadata catalog.
  * **Amazon Athena** is a serverless interactive query engine (built on Presto/Trino). It allows me to write standard SQL queries directly against the files sitting in S3 without ever "loading" them into a database.

### 5. Transformations (dbt)
* **dbt Core (`dbt-athena`):** dbt is the industry standard for transforming data in the warehouse. I utilized dbt to enforce data quality and implement the Medallion architecture:
  * **Silver Layer (`stg_crypto_prices`):** Unifies the historical backfill and live data, standardizes UNIX timestamps, and uses `ROW_NUMBER()` window functions to drop duplicate records where the live pipeline overlaps the backfill.
  * **Gold Layer (`fct_crypto_market_pulse`):** A materialized Parquet table that calculates business logic—rolling 24-hour moving averages and percentage changes—while applying timezone optimizations (Predicate Pushdown) to make the dashboard blazing fast.

### 6. Dashboard Integration
* **Streamlit:** To visualize the final Gold layer, I built a custom Python web application using Streamlit. Streamlit is lightweight, highly customizable, and integrates seamlessly with AWS via `awswrangler` (AWS SDK for pandas), allowing me to pull Athena query results directly into interactive Plotly charts.

---

## ⏱️ Strategic Batching vs. Streaming (Cost Optimization)
A core engineering decision in this project was architecting an **hourly micro-batch pipeline** rather than a live streaming pipeline. This was done strategically to maintain a $0 operational footprint by strictly adhering to free-tier provider limits:

* **CoinGecko API Rate Limits:** The free tier provides exactly 10,000 API calls per month. A streaming architecture (e.g., querying every minute) would require over 43,000 calls per month, resulting in blocked requests and exorbitant API fees. By fetching data hourly, the ingestion pipeline consumes only ~744 calls per month, leaving massive headroom.
* **dbt Cloud Allowances:** The dbt Cloud Developer tier restricts accounts to 3,000 successful job runs per month. Scheduling the transformation job hourly consumes exactly 744 runs per month.

This hourly orchestration represents the perfect balance between providing a near real-time analytical dashboard and engineering a highly cost-optimized, infinitely sustainable data product.

---

## 🏗️ Pipeline Flow

1. **The Backfill (One-Off):** A Python script fetches 1 year of historical data from CoinGecko, converts it to Parquet, and uploads it to the Bronze S3 bucket.
2. **Live Ingestion (Hourly Batch):** AWS EventBridge triggers the Dockerized AWS Lambda function every hour. Because the rule was activated immediately following the historical backfill, its natural execution time (11 minutes past the hour) perfectly maintains a continuous 60-minute interval. The function fetches the latest prices and drops a new Parquet file into the Bronze S3 bucket partitioned by `year/month/day/hour`.
3. **The Data Catalog:** An AWS Glue Crawler runs automatically at **15 minutes past every hour** (via cron schedule `15 * * * ? *`), detecting new S3 partitions and updating the Data Catalog.
4. **Transformation:** dbt Cloud triggers at **20 minutes past every hour**, running data quality tests, deduplicating the data, and materializing the optimized Gold table in Athena.
5. **Dashboard:** Streamlit queries the Gold table in Athena to visualize the market analytics.

---

```mermaid
graph TD
    %% Define Nodes
    API(CoinGecko API)
    
    subgraph Data Ingestion
        Backfill[Local Backfill Script]
        EventBridge((AWS EventBridge <br> Hourly Cron))
        Lambda[AWS Lambda <br> Dockerized]
    end
    
    subgraph Data Lake Storage
        Bronze[(S3 Bronze <br> Raw Parquet)]
        Gold[(S3 Gold <br> Optimized Parquet)]
    end
    
    subgraph Data Warehouse & Transformation
        Glue[AWS Glue Crawler]
        Athena[Amazon Athena]
        dbtCloud((dbt Cloud <br> Orchestration))
    end
    
    subgraph Presentation
        Streamlit([Streamlit Dashboard])
    end

    %% Define Flow
    API --> Backfill
    API --> Lambda
    EventBridge -. Triggers Hourly .-> Lambda
    
    Backfill ==>|1 Year History| Bronze
    Lambda ==>|Live Updates| Bronze
    
    Bronze --> Glue
    Glue -. Catalogs Metadata .-> Athena
    Athena <--> dbtCloud
    dbtCloud ==>|Cleans & Aggregates| Gold
    
    Gold --> Athena
    Athena ==>|awswrangler| Streamlit

    %% Styling
    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:black;
    classDef storage fill:#3F8624,stroke:#232F3E,stroke-width:2px,color:white;
    classDef compute fill:#00A4A6,stroke:#232F3E,stroke-width:2px,color:white;
    
    class EventBridge,Lambda,Glue,Athena aws;
    class Bronze,Gold storage;
    class dbtCloud,Streamlit,Backfill compute;
```

## 📂 Project Directory Structure

```text
crypto-pulse-lakehouse/
├── notebook/
│   └── explore_api.ipynb         # Initial API testing, validation, and schema exploration
├── src/
│   ├── historical_backfill.py    # Script to extract 1-year historical data and load to S3
│   └── lambda_function.py        # Dockerized AWS Lambda handler for live hourly ingestion
├── transform/                    # dbt project directory
│   ├── models/
│   │   ├── staging/              # Silver layer: stg_crypto_prices.sql (cleaning & deduplication)
│   │   └── marts/                # Gold layer: fct_crypto_market_pulse.sql (business logic)
│   ├── tests/                    # Custom dbt data quality tests
│   ├── dbt_project.yml           # dbt configuration
│   └── profiles.yml              # dbt-athena connection configuration
├── .env.example                  # Template for environment variables
├── .gitignore                    # Git ignore file for localized/sensitive files
├── app.py                        # Streamlit dashboard application
├── Dockerfile                    # Container definition for AWS Lambda deployment
├── main.tf                       # Terraform declarative infrastructure definitions
├── Makefile                      # Command shortcuts for infrastructure provisioning
├── pyproject.toml                # Python dependencies managed by 'uv'
├── uv.lock                       # Deterministic dependency lockfile
└── README.md                     # Project documentation
```
*(Note: Directories like `.venv`, `.terraform`, `logs/`, and `.env` are dynamically generated locally and excluded from version control).*

---

## 📊 The Dashboard
The Streamlit dashboard delivers a professional, trading-platform-style UI with interactive, dynamic analytical components driven by a global asset selector:

* **Global Control:** A unified dropdown menu that allows users to seamlessly switch between assets, instantly updating all downstream metrics and charts.
* **Top-Level Metrics:** Dynamic KPI cards highlighting the selected asset's current price, 24-hour percentage change, and total market cap.
* **Temporal Analysis:** An interactive Plotly time-series line chart visualizing the 7-day real-time price trend overlaid with a rolling 24-hour moving average.
* **Categorical Composition:** Dynamic Market Composition charts (a Donut chart and a custom-formatted Bar chart). These visuals compare the selected asset's market cap (formatted cleanly into billions) against the rest of the market.

---

## 🚀 Reproducibility (How to run this project)

This project implements a **Dockerized Makefile** approach. You do not need to install Terraform locally to deploy this infrastructure.

### Prerequisites
1. Docker installed and running.
2. An AWS Account with configured credentials (`~/.aws/credentials`).
3. A free CoinGecko API Key.

### Step 1: Environment Setup
Clone the repository, create a `.env` file for your API key, and install Python dependencies:
```bash
echo 'COINGECKO_API_KEY="your_api_key_here"' > .env
make setup
```

### Step 2: Deploy Infrastructure
Use the provided `Makefile` to deploy the AWS architecture via a HashiCorp Docker container:
```bash
make tf-init
make tf-apply
```
*(This creates the S3 buckets, IAM roles, ECR repository, Lambda function, EventBridge rule, and Glue Crawler).*

### Step 3: Deploy Lambda & Backfill Data
Build and push the Dockerized Python ingestion script to AWS ECR, then run the historical backfill script to seed your data lake:
```bash
make docker-push
make backfill
```

### Step 4: Run Transformations
Ensure your `transform/profiles.yml` points to the newly created S3 Gold bucket, then build the Medallion architecture:
```bash
make dbt-run
```

### Step 5: Launch the Dashboard
Start the Streamlit application locally:
```bash
make dashboard
```

### Teardown
To avoid AWS charges, destroy all infrastructure when finished:
```bash
make tf-destroy
```

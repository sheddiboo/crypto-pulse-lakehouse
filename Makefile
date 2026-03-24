# ==========================================
# Crypto Market Pulse - Project Makefile
# ==========================================

# --- Environment Variables ---
AWS_REGION = <YOUR_AWS_REGION>
AWS_ACCOUNT_ID = <YOUR_AWS_ACCOUNT_ID>
ECR_REPO = crypto-ingestion-lambda
ECR_URL = $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPO)

.PHONY: help setup tf-init tf-apply tf-destroy ecr-login docker-build docker-push backfill dbt-run dashboard

# Displays the help menu by default
help:
	@echo "Crypto Market Pulse - Available Commands:"
	@echo "  make setup         - Install local Python dependencies using uv"
	@echo "  make tf-init       - Initialize Terraform via Docker"
	@echo "  make tf-apply      - Apply Terraform infrastructure via Docker"
	@echo "  make tf-destroy    - Destroy Terraform infrastructure via Docker"
	@echo "  make docker-build  - Build the Lambda Docker image (AMD64)"
	@echo "  make docker-push   - Authenticate and push the Docker image to AWS ECR (Elastic Container Registry)"
	@echo "  make backfill      - Run the historical backfill script to seed S3"
	@echo "  make dbt-run       - Run the dbt transformation pipeline (Silver/Gold)"
	@echo "  make dashboard     - Launch the Streamlit dashboard locally"

# ==========================================
# Local Setup
# ==========================================
setup:
	@echo "Setting up local environment with uv..."
	uv pip install -r pyproject.toml
	@echo "Setup complete."

# ==========================================
# Infrastructure (Terraform via Docker)
# ==========================================
tf-init:
	@echo "Initializing Terraform..."
	docker run --rm -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest init

tf-apply:
	@echo "Deploying AWS Infrastructure..."
	docker run --rm -it -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest apply

tf-destroy:
	@echo "Destroying AWS Infrastructure..."
	docker run --rm -it -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest destroy

# ==========================================
# Docker and ECR (Elastic Container Registry) Deployment
# ==========================================
ecr-login:
	@echo "Authenticating with AWS ECR (Elastic Container Registry)..."
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

docker-build:
	@echo "Building Docker image for AWS Lambda..."
	docker build --platform linux/amd64 --provenance=false -t $(ECR_REPO) .

docker-push: ecr-login docker-build
	@echo "Pushing image to AWS ECR (Elastic Container Registry)..."
	docker tag $(ECR_REPO):latest $(ECR_URL):latest
	docker push $(ECR_URL):latest
	@echo "Image pushed successfully."

# ==========================================
# Data Operations
# ==========================================
backfill:
	@echo "Running historical data backfill..."
	python src/historical_backfill.py
	@echo "Backfill complete."

dbt-run:
	@echo "Running dbt transformations..."
	cd transform && dbt deps && dbt build
	@echo "Transformations complete."

# ==========================================
# Dashboard
# ==========================================
dashboard:
	@echo "Launching Streamlit Dashboard..."
	streamlit run app.py
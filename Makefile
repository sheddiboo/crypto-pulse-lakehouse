.PHONY: tf-init tf-apply tf-destroy ecr-login docker-build docker-push

# Initialize Terraform via Docker
tf-init:
	docker run --rm -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest init

# Apply Terraform via Docker
tf-apply:
	docker run --rm -it -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest apply

# Destroy Terraform via Docker
tf-destroy:
	docker run --rm -it -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest destroy

# ==========================================
# Docker and ECR Deployment
# ==========================================
AWS_REGION = eu-west-1
AWS_ACCOUNT_ID = 844479804638
ECR_REPO = crypto-ingestion-lambda
ECR_URL = $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPO)

# Authenticate Docker with your AWS Account
ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

# Build the Docker Image (Forcing AMD64 architecture and disabling provenance for AWS Lambda compatibility)
docker-build:
	docker build --platform linux/amd64 --provenance=false -t $(ECR_REPO) .
	
# Tag and Push the image to the cloud
docker-push: ecr-login docker-build
	docker tag $(ECR_REPO):latest $(ECR_URL):latest
	docker push $(ECR_URL):latest
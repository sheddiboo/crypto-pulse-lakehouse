.PHONY: tf-init tf-apply tf-destroy

# Initialize Terraform via Docker
tf-init:
	docker run --rm -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest init

# Apply Terraform via Docker
tf-apply:
	docker run --rm -it -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest apply

# Destroy Terraform via Docker
tf-destroy:
	docker run --rm -it -v $$(pwd):/workspace -v ~/.aws:/root/.aws -w /workspace --network host hashicorp/terraform:latest destroy
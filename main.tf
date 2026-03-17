# Provider Configuration
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = "eu-west-1"
}

# Random ID Generator for Unique Bucket Names
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# The Raw Data Lake Zone (Bronze)
resource "aws_s3_bucket" "raw_zone" {
  bucket        = "crypto-lake-raw-${random_id.bucket_suffix.hex}"
  force_destroy = true 
}

# The Optimized Data Lake Zone (Gold)
resource "aws_s3_bucket" "gold_zone" {
  bucket        = "crypto-lake-gold-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

# The Athena / Glue Data Catalog Database
# This allows Athena to query the files sitting in your S3 buckets.
resource "aws_glue_catalog_database" "crypto_db" {
  name        = "crypto_pulse_db"
  description = "Database for the Crypto Pulse Lakehouse"
}

# Elastic Container Registry (ECR)
resource "aws_ecr_repository" "lambda_docker_repo" {
  name         = "crypto-ingestion-lambda"
  force_delete = true
}

# IAM Execution Role for Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "crypto_lambda_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy: S3 and CloudWatch Logs
resource "aws_iam_role_policy" "lambda_s3_logs_policy" {
  name = "lambda_s3_logs_policy"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Effect   = "Allow"
        Resource = "${aws_s3_bucket.raw_zone.arn}/*"
      }
    ]
  })
}

# Output Variables
output "raw_bucket_name" {
  value = aws_s3_bucket.raw_zone.bucket
}

output "gold_bucket_name" {
  value = aws_s3_bucket.gold_zone.bucket
}

output "athena_database_name" {
  value = aws_glue_catalog_database.crypto_db.name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.lambda_docker_repo.repository_url
}
# ==========================================
# Provider Configuration
# ==========================================
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

# ==========================================
# Variables
# ==========================================
variable "coingecko_api_key" {
  description = "API Key for CoinGecko"
  type        = string
  sensitive   = true
}

# ==========================================
# Storage & Registry Infrastructure
# ==========================================
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
resource "aws_glue_catalog_database" "crypto_db" {
  name        = "crypto_pulse_db"
  description = "Database for the Crypto Pulse Lakehouse"
}

# Elastic Container Registry (ECR)
resource "aws_ecr_repository" "lambda_docker_repo" {
  name         = "crypto-ingestion-lambda"
  force_delete = true
}

# ==========================================
# Security & IAM Roles
# ==========================================
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

# ==========================================
# Compute: Lambda Function
# ==========================================
resource "aws_lambda_function" "crypto_ingestion_lambda" {
  function_name = "crypto-hourly-ingestion"
  role          = aws_iam_role.lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.lambda_docker_repo.repository_url}:latest"
  timeout       = 120 
  memory_size   = 256  # <-- Upgraded RAM for Pandas/PyArrow

  environment {
    variables = {
      RAW_S3_BUCKET     = aws_s3_bucket.raw_zone.bucket
      COINGECKO_API_KEY = var.coingecko_api_key
    }
  }
}

# ==========================================
# Automation: EventBridge (Cron Job)
# ==========================================
resource "aws_cloudwatch_event_rule" "hourly_trigger" {
  name                = "crypto-hourly-trigger"
  description         = "Fires every hour to trigger the crypto ingestion Lambda"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "trigger_lambda" {
  rule      = aws_cloudwatch_event_rule.hourly_trigger.name
  target_id = "IngestionLambda"
  arn       = aws_lambda_function.crypto_ingestion_lambda.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.crypto_ingestion_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly_trigger.arn
}

# ==========================================
# Output Variables
# ==========================================
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

# ==========================================
# Glue Crawler IAM Role
# ==========================================
resource "aws_iam_role" "glue_crawler_role" {
  name = "crypto_glue_crawler_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })
}

# Grant Glue permission to read S3 and write to CloudWatch logs
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_crawler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_read" {
  name = "glue_s3_read_policy"
  role = aws_iam_role.glue_crawler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Effect   = "Allow"
      Resource = ["${aws_s3_bucket.raw_zone.arn}", "${aws_s3_bucket.raw_zone.arn}/*"]
    }]
  })
}

# ==========================================
# Glue Crawler
# ==========================================
resource "aws_glue_crawler" "crypto_crawler" {
  database_name = aws_glue_catalog_database.crypto_db.name
  name          = "crypto-raw-crawler"
  role          = aws_iam_role.glue_crawler_role.arn

  s3_target {
    path = "s3://${aws_s3_bucket.raw_zone.bucket}/"
  }

  table_prefix = "raw_"
  
  # AUTOMATION ADDED: Runs at 15 minutes past the hour, every hour
  schedule = "cron(15 * * * ? *)"
}
# Science Talk - Main Terraform Configuration

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.18"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Optional: S3 backend for state management
  # Uncomment and configure when ready for team collaboration
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "talk/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile  # Uses default profile if null

  default_tags {
    tags = {
      Project     = var.project_display_name
      ManagedBy   = "Terraform"
      Environment = "production"
    }
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get current region
data "aws_region" "current" {}

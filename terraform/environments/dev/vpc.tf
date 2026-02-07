# Rung Dev Environment - VPC Configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }

  # Uncomment and configure for remote state (recommended for team use)
  # backend "s3" {
  #   bucket         = "rung-terraform-state"
  #   key            = "dev/vpc/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "rung-terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "rung"
      Environment = "dev"
      ManagedBy   = "terraform"
      HIPAA       = "true"
    }
  }
}

#------------------------------------------------------------------------------
# Variables
#------------------------------------------------------------------------------
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

#------------------------------------------------------------------------------
# S3 Variables
#------------------------------------------------------------------------------
variable "cors_allowed_origins" {
  description = "List of allowed origins for S3 CORS configuration"
  type        = list(string)
  default     = ["https://localhost:3000"]  # Update for production
}

#------------------------------------------------------------------------------
# Cognito Variables
#------------------------------------------------------------------------------
variable "cognito_callback_urls" {
  description = "List of allowed callback URLs after Cognito authentication"
  type        = list(string)
  default     = ["https://localhost:3000/auth/callback"]  # Update for production
}

variable "cognito_logout_urls" {
  description = "List of allowed logout URLs for Cognito"
  type        = list(string)
  default     = ["https://localhost:3000/logout"]  # Update for production
}

#------------------------------------------------------------------------------
# VPC Module
#------------------------------------------------------------------------------
module "vpc" {
  source = "../../modules/vpc"

  project_name = "rung"
  environment  = var.environment
  aws_region   = var.aws_region

  vpc_cidr             = "10.0.0.0/16"
  availability_zones   = ["us-east-1a", "us-east-1b"]
  private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true  # Cost saving for dev environment

  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    CostCenter = "rung-dev"
  }
}

#------------------------------------------------------------------------------
# Outputs
#------------------------------------------------------------------------------
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_azs" {
  description = "Private subnet availability zones"
  value       = module.vpc.private_subnet_azs
}

output "public_subnet_azs" {
  description = "Public subnet availability zones"
  value       = module.vpc.public_subnet_azs
}

output "nat_gateway_ips" {
  description = "NAT Gateway public IPs"
  value       = module.vpc.nat_gateway_public_ips
}

# DEPRECATED: Lambda has been replaced by FastAPI + ECS.
# This output is retained until the VPC module removes the Lambda security group.
output "lambda_security_group_id" {
  description = "DEPRECATED - Lambda security group ID (Lambda replaced by ECS)"
  value       = module.vpc.lambda_security_group_id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = module.vpc.rds_security_group_id
}

output "s3_vpc_endpoint_id" {
  description = "S3 VPC endpoint ID"
  value       = module.vpc.s3_vpc_endpoint_id
}

output "bedrock_vpc_endpoint_id" {
  description = "Bedrock VPC endpoint ID"
  value       = module.vpc.bedrock_vpc_endpoint_id
}

output "bedrock_runtime_vpc_endpoint_id" {
  description = "Bedrock Runtime VPC endpoint ID"
  value       = module.vpc.bedrock_runtime_vpc_endpoint_id
}

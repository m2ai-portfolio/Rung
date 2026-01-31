# Rung Dev Environment - RDS and KMS Configuration
# This file imports the VPC module and creates KMS + RDS resources

#------------------------------------------------------------------------------
# KMS Module - Encryption Keys
#------------------------------------------------------------------------------
module "kms" {
  source = "../../modules/kms"

  project_name            = "rung"
  environment             = var.environment
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    CostCenter = "rung-dev"
  }
}

#------------------------------------------------------------------------------
# RDS Module - PostgreSQL Database
#------------------------------------------------------------------------------
module "rds" {
  source = "../../modules/rds"

  project_name = "rung"
  environment  = var.environment

  # Database configuration
  database_name         = "rung"
  engine_version        = "15"
  instance_class        = "db.r6g.large"
  allocated_storage     = 100
  max_allocated_storage = 500

  # High availability
  multi_az = true

  # Network configuration (from VPC module)
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.rds_security_group_id]

  # Encryption (from KMS module)
  kms_key_arn         = module.kms.rds_key_arn
  secrets_kms_key_arn = module.kms.secrets_key_arn

  # Backup configuration - HIPAA compliant
  backup_retention_period = 35

  # Monitoring
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  monitoring_interval                   = 60

  # Protection
  deletion_protection = false  # Set to true in production
  skip_final_snapshot = true   # Set to false in production

  tags = {
    CostCenter = "rung-dev"
  }

  depends_on = [module.vpc, module.kms]
}

#------------------------------------------------------------------------------
# KMS Outputs
#------------------------------------------------------------------------------
output "kms_master_key_arn" {
  description = "Master KMS key ARN"
  value       = module.kms.master_key_arn
}

output "kms_rds_key_arn" {
  description = "RDS KMS key ARN"
  value       = module.kms.rds_key_arn
}

output "kms_s3_key_arn" {
  description = "S3 KMS key ARN"
  value       = module.kms.s3_key_arn
}

output "kms_field_key_arn" {
  description = "Field-level encryption KMS key ARN"
  value       = module.kms.field_key_arn
}

output "kms_secrets_key_arn" {
  description = "Secrets Manager KMS key ARN"
  value       = module.kms.secrets_key_arn
}

#------------------------------------------------------------------------------
# RDS Outputs
#------------------------------------------------------------------------------
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
}

output "rds_address" {
  description = "RDS instance address (hostname)"
  value       = module.rds.db_instance_address
}

output "rds_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "rds_database_name" {
  description = "Name of the database"
  value       = module.rds.db_instance_name
}

output "rds_credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret containing DB credentials"
  value       = module.rds.db_credentials_secret_arn
}

output "rds_encrypted" {
  description = "Whether RDS is encrypted"
  value       = module.rds.db_instance_encrypted
}

output "rds_multi_az" {
  description = "Whether Multi-AZ is enabled"
  value       = module.rds.db_instance_multi_az
}

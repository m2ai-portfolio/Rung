# RDS Module Outputs

#------------------------------------------------------------------------------
# RDS Instance
#------------------------------------------------------------------------------
output "db_instance_id" {
  description = "ID of the RDS instance"
  value       = aws_db_instance.main.id
}

output "db_instance_identifier" {
  description = "Identifier of the RDS instance"
  value       = aws_db_instance.main.identifier
}

output "db_instance_arn" {
  description = "ARN of the RDS instance"
  value       = aws_db_instance.main.arn
}

output "db_instance_address" {
  description = "Address (hostname) of the RDS instance"
  value       = aws_db_instance.main.address
}

output "db_instance_endpoint" {
  description = "Connection endpoint of the RDS instance"
  value       = aws_db_instance.main.endpoint
}

output "db_instance_port" {
  description = "Port of the RDS instance"
  value       = aws_db_instance.main.port
}

output "db_instance_name" {
  description = "Name of the database"
  value       = aws_db_instance.main.db_name
}

output "db_instance_username" {
  description = "Master username for the database"
  value       = aws_db_instance.main.username
  sensitive   = true
}

#------------------------------------------------------------------------------
# Encryption Status
#------------------------------------------------------------------------------
output "db_instance_encrypted" {
  description = "Whether the RDS instance is encrypted"
  value       = aws_db_instance.main.storage_encrypted
}

output "db_instance_kms_key_id" {
  description = "KMS key ID used for encryption"
  value       = aws_db_instance.main.kms_key_id
}

#------------------------------------------------------------------------------
# High Availability
#------------------------------------------------------------------------------
output "db_instance_multi_az" {
  description = "Whether Multi-AZ is enabled"
  value       = aws_db_instance.main.multi_az
}

output "db_instance_availability_zone" {
  description = "Availability zone of the RDS instance"
  value       = aws_db_instance.main.availability_zone
}

#------------------------------------------------------------------------------
# Network
#------------------------------------------------------------------------------
output "db_subnet_group_name" {
  description = "Name of the DB subnet group"
  value       = aws_db_subnet_group.main.name
}

output "db_subnet_group_arn" {
  description = "ARN of the DB subnet group"
  value       = aws_db_subnet_group.main.arn
}

#------------------------------------------------------------------------------
# Secrets Manager
#------------------------------------------------------------------------------
output "db_credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret containing DB credentials"
  value       = aws_secretsmanager_secret.rds_credentials.arn
}

output "db_credentials_secret_name" {
  description = "Name of the Secrets Manager secret containing DB credentials"
  value       = aws_secretsmanager_secret.rds_credentials.name
}

#------------------------------------------------------------------------------
# Parameter Group
#------------------------------------------------------------------------------
output "db_parameter_group_name" {
  description = "Name of the DB parameter group"
  value       = aws_db_parameter_group.main.name
}

output "db_parameter_group_arn" {
  description = "ARN of the DB parameter group"
  value       = aws_db_parameter_group.main.arn
}

#------------------------------------------------------------------------------
# Monitoring
#------------------------------------------------------------------------------
output "db_monitoring_role_arn" {
  description = "ARN of the enhanced monitoring IAM role"
  value       = aws_iam_role.rds_monitoring.arn
}

output "performance_insights_enabled" {
  description = "Whether Performance Insights is enabled"
  value       = aws_db_instance.main.performance_insights_enabled
}

#------------------------------------------------------------------------------
# Connection String (for reference - use Secrets Manager in practice)
#------------------------------------------------------------------------------
output "db_connection_info" {
  description = "Database connection information (use Secrets Manager for credentials)"
  value = {
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    database = aws_db_instance.main.db_name
    engine   = "postgresql"
  }
}

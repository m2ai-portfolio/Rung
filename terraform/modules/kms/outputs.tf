# KMS Module Outputs

#------------------------------------------------------------------------------
# Master Key
#------------------------------------------------------------------------------
output "master_key_id" {
  description = "ID of the master KMS key"
  value       = aws_kms_key.master.key_id
}

output "master_key_arn" {
  description = "ARN of the master KMS key"
  value       = aws_kms_key.master.arn
}

output "master_key_alias" {
  description = "Alias of the master KMS key"
  value       = aws_kms_alias.master.name
}

#------------------------------------------------------------------------------
# RDS Key
#------------------------------------------------------------------------------
output "rds_key_id" {
  description = "ID of the RDS KMS key"
  value       = aws_kms_key.rds.key_id
}

output "rds_key_arn" {
  description = "ARN of the RDS KMS key"
  value       = aws_kms_key.rds.arn
}

output "rds_key_alias" {
  description = "Alias of the RDS KMS key"
  value       = aws_kms_alias.rds.name
}

#------------------------------------------------------------------------------
# S3 Key
#------------------------------------------------------------------------------
output "s3_key_id" {
  description = "ID of the S3 KMS key"
  value       = aws_kms_key.s3.key_id
}

output "s3_key_arn" {
  description = "ARN of the S3 KMS key"
  value       = aws_kms_key.s3.arn
}

output "s3_key_alias" {
  description = "Alias of the S3 KMS key"
  value       = aws_kms_alias.s3.name
}

#------------------------------------------------------------------------------
# Field-Level Encryption Key
#------------------------------------------------------------------------------
output "field_key_id" {
  description = "ID of the field-level encryption KMS key"
  value       = aws_kms_key.field.key_id
}

output "field_key_arn" {
  description = "ARN of the field-level encryption KMS key"
  value       = aws_kms_key.field.arn
}

output "field_key_alias" {
  description = "Alias of the field-level encryption KMS key"
  value       = aws_kms_alias.field.name
}

#------------------------------------------------------------------------------
# Secrets Manager Key
#------------------------------------------------------------------------------
output "secrets_key_id" {
  description = "ID of the Secrets Manager KMS key"
  value       = aws_kms_key.secrets.key_id
}

output "secrets_key_arn" {
  description = "ARN of the Secrets Manager KMS key"
  value       = aws_kms_key.secrets.arn
}

output "secrets_key_alias" {
  description = "Alias of the Secrets Manager KMS key"
  value       = aws_kms_alias.secrets.name
}

#------------------------------------------------------------------------------
# All Keys (for convenience)
#------------------------------------------------------------------------------
output "all_key_arns" {
  description = "Map of all KMS key ARNs"
  value = {
    master  = aws_kms_key.master.arn
    rds     = aws_kms_key.rds.arn
    s3      = aws_kms_key.s3.arn
    field   = aws_kms_key.field.arn
    secrets = aws_kms_key.secrets.arn
  }
}

output "all_key_aliases" {
  description = "Map of all KMS key aliases"
  value = {
    master  = aws_kms_alias.master.name
    rds     = aws_kms_alias.rds.name
    s3      = aws_kms_alias.s3.name
    field   = aws_kms_alias.field.name
    secrets = aws_kms_alias.secrets.name
  }
}

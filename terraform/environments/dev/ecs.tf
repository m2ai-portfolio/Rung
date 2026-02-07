# Rung Dev Environment - ECS Fargate Deployment
# Deploys Rung FastAPI application to ECS Fargate with ALB integration

#------------------------------------------------------------------------------
# Application Load Balancer (if not already created)
#------------------------------------------------------------------------------
resource "aws_lb" "rung" {
  name               = "rung-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [module.vpc.alb_security_group_id]
  subnets            = module.vpc.public_subnet_ids

  enable_deletion_protection = false
  enable_http2               = true
  enable_cross_zone_load_balancing = true

  tags = {
    Name        = "rung-${var.environment}-alb"
    CostCenter  = "rung-dev"
    HIPAA       = "true"
  }

  depends_on = [module.vpc]
}

#------------------------------------------------------------------------------
# ECS Module - Container Orchestration
#------------------------------------------------------------------------------
module "ecs" {
  source = "../../modules/ecs"

  project_name = "rung"
  environment  = var.environment
  aws_region   = var.aws_region

  # Container configuration - dev sizing
  cpu                = 512    # 0.5 vCPU for cost saving
  memory             = 1024   # 1 GB memory
  container_port     = 8000
  log_level          = "INFO"

  # Service configuration
  desired_count  = 1
  max_capacity   = 3    # Allow scaling to 3 instances max

  # Network configuration
  vpc_id                          = module.vpc.vpc_id
  private_subnet_ids              = module.vpc.private_subnet_ids
  alb_arn                         = aws_lb.rung.arn
  alb_security_group_id           = module.vpc.alb_security_group_id
  rds_security_group_id           = module.vpc.rds_security_group_id
  vpc_endpoints_security_group_id = module.vpc.vpc_endpoints_security_group_id
  s3_vpc_endpoint_prefix_list_id  = module.vpc.s3_vpc_endpoint_prefix_list_id

  # Database configuration
  database_secret_arn           = module.rds.db_credentials_secret_arn
  database_secret_kms_key_arn   = module.kms.secrets_key_arn

  # KMS keys
  ecr_kms_key_arn          = module.kms.master_key_arn
  logs_kms_key_id          = module.kms.master_key_id
  s3_kms_key_arn           = module.kms.s3_key_arn
  field_encryption_key_arn = module.kms.field_key_arn

  # S3 configuration
  s3_bucket_name = module.s3.voice_memos_bucket_name

  # Logging
  log_retention_days = 365  # 1 year for HIPAA compliance

  tags = {
    CostCenter = "rung-dev"
  }

  depends_on = [
    module.vpc,
    module.rds,
    module.kms,
    module.s3,
    aws_lb.rung,
  ]
}

#------------------------------------------------------------------------------
# RDS ingress from ECS (ECS SG created in ECS module, RDS SG in VPC module)
#------------------------------------------------------------------------------
resource "aws_security_group_rule" "rds_from_ecs" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = module.vpc.rds_security_group_id
  source_security_group_id = module.ecs.ecs_security_group_id
  description              = "PostgreSQL from ECS Fargate tasks"
}

#------------------------------------------------------------------------------
# ECS Outputs
#------------------------------------------------------------------------------
output "ecr_repository_url" {
  description = "ECR repository URL for pushing images"
  value       = module.ecs.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.ecs_cluster_name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.ecs.ecs_service_name
}

output "alb_dns_name" {
  description = "DNS name of the ALB"
  value       = aws_lb.rung.dns_name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for ECS container logs"
  value       = module.ecs.cloudwatch_log_group_name
}

output "task_definition_arn" {
  description = "ECS task definition ARN"
  value       = module.ecs.task_definition_arn
}

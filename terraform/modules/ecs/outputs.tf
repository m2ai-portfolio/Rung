# ECS Module Outputs

#------------------------------------------------------------------------------
# ECR Repository
#------------------------------------------------------------------------------
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.rung.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.rung.arn
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.rung.name
}

#------------------------------------------------------------------------------
# ECS Cluster
#------------------------------------------------------------------------------
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

#------------------------------------------------------------------------------
# ECS Service
#------------------------------------------------------------------------------
output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.rung.name
}

output "ecs_service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.rung.arn
}

#------------------------------------------------------------------------------
# Task Definition
#------------------------------------------------------------------------------
output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.rung.arn
}

output "task_definition_family" {
  description = "Family name of the ECS task definition"
  value       = aws_ecs_task_definition.rung.family
}

output "task_definition_revision" {
  description = "Revision of the ECS task definition"
  value       = aws_ecs_task_definition.rung.revision
}

#------------------------------------------------------------------------------
# Target Group
#------------------------------------------------------------------------------
output "alb_target_group_arn" {
  description = "ARN of the ALB target group"
  value       = aws_lb_target_group.rung.arn
}

output "alb_target_group_name" {
  description = "Name of the ALB target group"
  value       = aws_lb_target_group.rung.name
}

#------------------------------------------------------------------------------
# CloudWatch Logs
#------------------------------------------------------------------------------
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs.arn
}

#------------------------------------------------------------------------------
# IAM Roles
#------------------------------------------------------------------------------
output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task_role.arn
}

#------------------------------------------------------------------------------
# Security Group
#------------------------------------------------------------------------------
output "ecs_security_group_id" {
  description = "ID of the ECS security group"
  value       = aws_security_group.ecs.id
}

#------------------------------------------------------------------------------
# Auto Scaling
#------------------------------------------------------------------------------
output "autoscaling_target_arn" {
  description = "ARN of the auto scaling target"
  value       = aws_appautoscaling_target.ecs_target.arn
}

# =============================================================================
# Rung Monitoring Module - Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# SNS Topics
# -----------------------------------------------------------------------------

output "security_alerts_topic_arn" {
  description = "ARN of the security alerts SNS topic"
  value       = aws_sns_topic.security_alerts.arn
}

output "operational_alerts_topic_arn" {
  description = "ARN of the operational alerts SNS topic"
  value       = aws_sns_topic.operational_alerts.arn
}

# -----------------------------------------------------------------------------
# Log Groups
# -----------------------------------------------------------------------------

output "api_gateway_log_group_name" {
  description = "Name of the API Gateway log group"
  value       = aws_cloudwatch_log_group.api_gateway.name
}

output "api_gateway_log_group_arn" {
  description = "ARN of the API Gateway log group"
  value       = aws_cloudwatch_log_group.api_gateway.arn
}

output "application_log_group_name" {
  description = "Name of the application log group"
  value       = aws_cloudwatch_log_group.application.name
}

output "application_log_group_arn" {
  description = "ARN of the application log group"
  value       = aws_cloudwatch_log_group.application.arn
}

output "ecs_log_group_name" {
  description = "Name of the ECS log group"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "ecs_log_group_arn" {
  description = "ARN of the ECS log group"
  value       = aws_cloudwatch_log_group.ecs.arn
}

output "audit_log_group_name" {
  description = "Name of the audit log group"
  value       = aws_cloudwatch_log_group.audit.name
}

output "audit_log_group_arn" {
  description = "ARN of the audit log group"
  value       = aws_cloudwatch_log_group.audit.arn
}

output "security_log_group_name" {
  description = "Name of the security log group"
  value       = aws_cloudwatch_log_group.security.name
}

output "security_log_group_arn" {
  description = "ARN of the security log group"
  value       = aws_cloudwatch_log_group.security.arn
}


# -----------------------------------------------------------------------------
# Alarms
# -----------------------------------------------------------------------------

output "alarm_arns" {
  description = "Map of alarm names to ARNs"
  value = {
    failed_auth_spike   = aws_cloudwatch_metric_alarm.failed_auth_spike.arn
    isolation_bypass    = aws_cloudwatch_metric_alarm.isolation_bypass.arn
    phi_external_api    = aws_cloudwatch_metric_alarm.phi_external_api.arn
    authz_failures      = aws_cloudwatch_metric_alarm.authz_failures_spike.arn
    api_error_rate      = aws_cloudwatch_metric_alarm.api_error_rate.arn
    high_phi_access     = aws_cloudwatch_metric_alarm.high_phi_access.arn
    phi_access_anomaly  = aws_cloudwatch_metric_alarm.phi_access_anomaly.arn
  }
}

# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "dashboard_arn" {
  description = "ARN of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_arn
}

# -----------------------------------------------------------------------------
# Log Retention
# -----------------------------------------------------------------------------

output "log_retention_days" {
  description = "Log retention period in days"
  value       = local.hipaa_retention_days
}

# =============================================================================
# Rung Monitoring Module - CloudWatch Logs, Metrics, and Alerts
# =============================================================================
#
# This module creates:
# - CloudWatch Log Groups with 7-year retention (HIPAA requirement)
# - Metric filters for security events
# - CloudWatch alarms for anomaly detection
# - SNS topics for alert routing
# - Dashboard for system overview
#
# =============================================================================

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# Local Variables
# -----------------------------------------------------------------------------

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  common_tags = merge(var.tags, {
    Module      = "monitoring"
    Environment = var.environment
  })

  # 7 years in days (HIPAA retention requirement)
  hipaa_retention_days = 2557
}

# -----------------------------------------------------------------------------
# SNS Topics for Alerts
# -----------------------------------------------------------------------------

resource "aws_sns_topic" "security_alerts" {
  name              = "rung-security-alerts-${var.environment}"
  kms_master_key_id = var.kms_key_id

  tags = merge(local.common_tags, {
    Name = "rung-security-alerts-${var.environment}"
  })
}

resource "aws_sns_topic" "operational_alerts" {
  name              = "rung-operational-alerts-${var.environment}"
  kms_master_key_id = var.kms_key_id

  tags = merge(local.common_tags, {
    Name = "rung-operational-alerts-${var.environment}"
  })
}

resource "aws_sns_topic_policy" "security_alerts" {
  arn = aws_sns_topic.security_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchAlarms"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.security_alerts.arn
        Condition = {
          ArnLike = {
            "aws:SourceArn" = "arn:aws:cloudwatch:${local.region}:${local.account_id}:alarm:*"
          }
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Groups (HIPAA 7-year retention)
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/rung-${var.environment}"
  retention_in_days = local.hipaa_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(local.common_tags, {
    Name     = "rung-api-gateway-logs"
    PHI      = "false"
    LogType  = "api-access"
  })
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/rung-${var.environment}"
  retention_in_days = local.hipaa_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(local.common_tags, {
    Name     = "rung-lambda-logs"
    PHI      = "false"
    LogType  = "application"
  })
}

resource "aws_cloudwatch_log_group" "audit" {
  name              = "/rung/audit/${var.environment}"
  retention_in_days = local.hipaa_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(local.common_tags, {
    Name     = "rung-audit-logs"
    PHI      = "false"
    LogType  = "audit"
    HIPAA    = "required"
  })
}

resource "aws_cloudwatch_log_group" "security" {
  name              = "/rung/security/${var.environment}"
  retention_in_days = local.hipaa_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(local.common_tags, {
    Name     = "rung-security-logs"
    PHI      = "false"
    LogType  = "security"
    HIPAA    = "required"
  })
}

resource "aws_cloudwatch_log_group" "n8n" {
  name              = "/rung/n8n/${var.environment}"
  retention_in_days = local.hipaa_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(local.common_tags, {
    Name     = "rung-n8n-logs"
    PHI      = "false"
    LogType  = "workflow"
  })
}

# -----------------------------------------------------------------------------
# Metric Filters - Security Events
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_metric_filter" "failed_authentication" {
  name           = "rung-failed-auth-${var.environment}"
  pattern        = "{ $.event_type = \"authentication\" && $.result = \"failure\" }"
  log_group_name = aws_cloudwatch_log_group.security.name

  metric_transformation {
    name          = "FailedAuthentication"
    namespace     = "Rung/Security"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "phi_access" {
  name           = "rung-phi-access-${var.environment}"
  pattern        = "{ $.resource_type = \"client\" || $.resource_type = \"session\" || $.resource_type = \"clinical_brief\" }"
  log_group_name = aws_cloudwatch_log_group.audit.name

  metric_transformation {
    name          = "PHIAccess"
    namespace     = "Rung/Audit"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "couples_merge" {
  name           = "rung-couples-merge-${var.environment}"
  pattern        = "{ $.event_type = \"couples_merge\" }"
  log_group_name = aws_cloudwatch_log_group.audit.name

  metric_transformation {
    name          = "CouplesMerge"
    namespace     = "Rung/Audit"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "isolation_invoked" {
  name           = "rung-isolation-invoked-${var.environment}"
  pattern        = "{ $.isolation_invoked = true }"
  log_group_name = aws_cloudwatch_log_group.audit.name

  metric_transformation {
    name          = "IsolationLayerInvoked"
    namespace     = "Rung/Security"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "isolation_not_invoked" {
  name           = "rung-isolation-not-invoked-${var.environment}"
  pattern        = "{ $.event_type = \"couples_merge\" && $.isolation_invoked = false }"
  log_group_name = aws_cloudwatch_log_group.audit.name

  metric_transformation {
    name          = "IsolationLayerBypassed"
    namespace     = "Rung/Security"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "external_api_phi" {
  name           = "rung-external-api-phi-${var.environment}"
  pattern        = "{ $.event_type = \"external_api_call\" && $.phi_detected = true }"
  log_group_name = aws_cloudwatch_log_group.security.name

  metric_transformation {
    name          = "PHIInExternalAPI"
    namespace     = "Rung/Security"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "rung-api-errors-${var.environment}"
  pattern        = "{ $.status >= 500 }"
  log_group_name = aws_cloudwatch_log_group.api_gateway.name

  metric_transformation {
    name          = "APIErrors"
    namespace     = "Rung/Application"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "authorization_failures" {
  name           = "rung-authz-failures-${var.environment}"
  pattern        = "{ $.status = 403 }"
  log_group_name = aws_cloudwatch_log_group.api_gateway.name

  metric_transformation {
    name          = "AuthorizationFailures"
    namespace     = "Rung/Security"
    value         = "1"
    default_value = "0"
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms - Security (P1/P2)
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "failed_auth_spike" {
  alarm_name          = "rung-failed-auth-spike-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FailedAuthentication"
  namespace           = "Rung/Security"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "SECURITY ALERT: More than 10 failed authentications in 5 minutes"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.security_alerts.arn]
  ok_actions    = [aws_sns_topic.security_alerts.arn]

  tags = merge(local.common_tags, {
    Severity = "P2"
    Type     = "Security"
  })
}

resource "aws_cloudwatch_metric_alarm" "isolation_bypass" {
  alarm_name          = "rung-isolation-bypass-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "IsolationLayerBypassed"
  namespace           = "Rung/Security"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "CRITICAL SECURITY ALERT: Isolation layer bypassed in couples merge"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.security_alerts.arn]

  tags = merge(local.common_tags, {
    Severity = "P1"
    Type     = "Security"
  })
}

resource "aws_cloudwatch_metric_alarm" "phi_external_api" {
  alarm_name          = "rung-phi-external-api-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "PHIInExternalAPI"
  namespace           = "Rung/Security"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "CRITICAL SECURITY ALERT: PHI detected in external API call"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.security_alerts.arn]

  tags = merge(local.common_tags, {
    Severity = "P1"
    Type     = "Security"
  })
}

resource "aws_cloudwatch_metric_alarm" "authz_failures_spike" {
  alarm_name          = "rung-authz-failures-spike-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "AuthorizationFailures"
  namespace           = "Rung/Security"
  period              = "300"
  statistic           = "Sum"
  threshold           = "20"
  alarm_description   = "SECURITY ALERT: High number of authorization failures"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.security_alerts.arn]
  ok_actions    = [aws_sns_topic.security_alerts.arn]

  tags = merge(local.common_tags, {
    Severity = "P2"
    Type     = "Security"
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms - Operational (P3/P4)
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "rung-api-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "APIErrors"
  namespace           = "Rung/Application"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "OPERATIONAL ALERT: Elevated API error rate"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.operational_alerts.arn]
  ok_actions    = [aws_sns_topic.operational_alerts.arn]

  tags = merge(local.common_tags, {
    Severity = "P3"
    Type     = "Operational"
  })
}

resource "aws_cloudwatch_metric_alarm" "high_phi_access" {
  alarm_name          = "rung-high-phi-access-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "PHIAccess"
  namespace           = "Rung/Audit"
  period              = "3600"
  statistic           = "Sum"
  threshold           = "1000"
  alarm_description   = "AUDIT ALERT: Unusually high PHI access volume"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.security_alerts.arn]

  tags = merge(local.common_tags, {
    Severity = "P2"
    Type     = "Audit"
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Anomaly Detection
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "phi_access_anomaly" {
  alarm_name          = "rung-phi-access-anomaly-${var.environment}"
  comparison_operator = "GreaterThanUpperThreshold"
  evaluation_periods  = "2"
  threshold_metric_id = "ad1"
  alarm_description   = "ANOMALY ALERT: Unusual PHI access pattern detected"
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "m1"
    return_data = true

    metric {
      metric_name = "PHIAccess"
      namespace   = "Rung/Audit"
      period      = "300"
      stat        = "Sum"
    }
  }

  metric_query {
    id          = "ad1"
    expression  = "ANOMALY_DETECTION_BAND(m1, 2)"
    label       = "PHI Access Anomaly Band"
    return_data = true
  }

  alarm_actions = [aws_sns_topic.security_alerts.arn]

  tags = merge(local.common_tags, {
    Severity = "P2"
    Type     = "Anomaly"
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Dashboard
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "rung-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 1
        properties = {
          markdown = "# Rung System Dashboard - ${upper(var.environment)}"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 1
        width  = 8
        height = 6
        properties = {
          title  = "Security Events"
          region = local.region
          metrics = [
            ["Rung/Security", "FailedAuthentication", { label = "Failed Auth" }],
            [".", "AuthorizationFailures", { label = "Authz Failures" }],
            [".", "IsolationLayerBypassed", { label = "Isolation Bypass", color = "#d62728" }],
            [".", "PHIInExternalAPI", { label = "PHI External API", color = "#d62728" }]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 1
        width  = 8
        height = 6
        properties = {
          title  = "Audit Events"
          region = local.region
          metrics = [
            ["Rung/Audit", "PHIAccess", { label = "PHI Access" }],
            [".", "CouplesMerge", { label = "Couples Merge" }],
            ["Rung/Security", "IsolationLayerInvoked", { label = "Isolation Invoked" }]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 1
        width  = 8
        height = 6
        properties = {
          title  = "API Health"
          region = local.region
          metrics = [
            ["Rung/Application", "APIErrors", { label = "5xx Errors", color = "#d62728" }]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "alarm"
        x      = 0
        y      = 7
        width  = 24
        height = 4
        properties = {
          title  = "Active Alarms"
          alarms = [
            aws_cloudwatch_metric_alarm.failed_auth_spike.arn,
            aws_cloudwatch_metric_alarm.isolation_bypass.arn,
            aws_cloudwatch_metric_alarm.phi_external_api.arn,
            aws_cloudwatch_metric_alarm.authz_failures_spike.arn,
            aws_cloudwatch_metric_alarm.api_error_rate.arn
          ]
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Insights Saved Queries
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_query_definition" "phi_access_by_user" {
  name = "Rung/Audit/PHI-Access-By-User"

  log_group_names = [
    aws_cloudwatch_log_group.audit.name
  ]

  query_string = <<-EOT
    fields @timestamp, user_id, resource_type, resource_id, action
    | filter resource_type in ['client', 'session', 'clinical_brief', 'client_guide']
    | stats count() as access_count by user_id
    | sort access_count desc
    | limit 20
  EOT
}

resource "aws_cloudwatch_query_definition" "failed_auth_analysis" {
  name = "Rung/Security/Failed-Auth-Analysis"

  log_group_names = [
    aws_cloudwatch_log_group.security.name
  ]

  query_string = <<-EOT
    fields @timestamp, ip_address, user_agent, @message
    | filter event_type = 'authentication' and result = 'failure'
    | stats count() as failures by ip_address, bin(5m)
    | sort failures desc
  EOT
}

resource "aws_cloudwatch_query_definition" "couples_merge_audit" {
  name = "Rung/Audit/Couples-Merge-Audit"

  log_group_names = [
    aws_cloudwatch_log_group.audit.name
  ]

  query_string = <<-EOT
    fields @timestamp, therapist_id, couple_link_id, session_id, isolation_invoked, action, result_summary
    | filter event_type = 'couples_merge'
    | sort @timestamp desc
    | limit 100
  EOT
}

resource "aws_cloudwatch_query_definition" "isolation_verification" {
  name = "Rung/Security/Isolation-Verification"

  log_group_names = [
    aws_cloudwatch_log_group.audit.name
  ]

  query_string = <<-EOT
    fields @timestamp, event_type, isolation_invoked, couple_link_id
    | filter event_type = 'couples_merge'
    | filter isolation_invoked = false
    | sort @timestamp desc
  EOT
}

resource "aws_cloudwatch_query_definition" "external_api_phi_check" {
  name = "Rung/Security/External-API-PHI-Check"

  log_group_names = [
    aws_cloudwatch_log_group.security.name
  ]

  query_string = <<-EOT
    fields @timestamp, api_endpoint, phi_detected, query_blocked, @message
    | filter event_type = 'external_api_call'
    | filter phi_detected = true or query_blocked = true
    | sort @timestamp desc
  EOT
}

resource "aws_cloudwatch_query_definition" "error_analysis" {
  name = "Rung/Application/Error-Analysis"

  log_group_names = [
    aws_cloudwatch_log_group.lambda.name,
    aws_cloudwatch_log_group.api_gateway.name
  ]

  query_string = <<-EOT
    fields @timestamp, @message, @logStream
    | filter @message like /ERROR|Exception|error/
    | sort @timestamp desc
    | limit 100
  EOT
}

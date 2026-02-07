# Rung ECS Module - Fargate Container Orchestration
# Deploys Rung FastAPI application to ECS Fargate with ALB integration
# HIPAA-compliant with CloudWatch logging and security best practices

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    HIPAA       = "true"
    Component   = "ecs"
  })
}

#------------------------------------------------------------------------------
# ECR Repository - Container Image Storage
#------------------------------------------------------------------------------
resource "aws_ecr_repository" "rung" {
  name                 = "${local.name_prefix}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.ecr_kms_key_arn
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecr"
  })
}

# ECR Repository policy for push/pull
resource "aws_ecr_repository_policy" "rung" {
  repository = aws_ecr_repository.rung.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowECSTaskExecutionRole"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ecs_task_execution_role.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:DescribeImages",
          "ecr:DescribeRepositories",
        ]
      }
    ]
  })
}

# ECR lifecycle policy to keep only recent images
resource "aws_ecr_lifecycle_policy" "rung" {
  repository = aws_ecr_repository.rung.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

#------------------------------------------------------------------------------
# CloudWatch Log Group - Container Logs
#------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/aws/ecs/${local.name_prefix}"
  retention_in_days = var.log_retention_days

  kms_key_id = var.logs_kms_key_id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-logs"
  })
}

#------------------------------------------------------------------------------
# ECS Cluster
#------------------------------------------------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cluster"
  })
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

#------------------------------------------------------------------------------
# ECS Task Definition - Container Configuration
#------------------------------------------------------------------------------
resource "aws_ecs_task_definition" "rung" {
  family                   = local.name_prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "rung"
      image     = "${aws_ecr_repository.rung.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]

      # Health check - critical for load balancer
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }

      # Environment variables (non-sensitive)
      environment = [
        {
          name  = "RUNG_ENV"
          value = var.environment
        },
        {
          name  = "PORT"
          value = tostring(var.container_port)
        },
        {
          name  = "LOG_LEVEL"
          value = var.log_level
        }
      ]

      # Secrets from Secrets Manager (sensitive configuration)
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${var.database_secret_arn}:password::"
        }
      ]

      # Logging configuration
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "rung"
        }
      }
    }
  ])

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-task-definition"
  })

  depends_on = [
    aws_iam_role_policy.ecs_task_role_policy,
    aws_iam_role_policy.ecs_task_execution_role_policy,
  ]
}

#------------------------------------------------------------------------------
# ALB Target Group - Service Health Checks
#------------------------------------------------------------------------------
resource "aws_lb_target_group" "rung" {
  name        = "${local.name_prefix}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-tg"
  })
}

#------------------------------------------------------------------------------
# ECS Service - Deployment Configuration
#------------------------------------------------------------------------------
resource "aws_ecs_service" "rung" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.rung.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.rung.arn
    container_name   = "rung"
    container_port   = var.container_port
  }

  # Deployment circuit breaker - automatic rollback on failure
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # Deployment strategy (ROLLING is default, no config needed for basic setup)
  # For canary/blue-green: use external tools like Flagger or CodeDeploy

  # Enable service registries if using Service Discovery
  depends_on = [
    aws_lb_listener.rung,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-service"
  })

  lifecycle {
    ignore_changes = [desired_count]  # Allow auto-scaling to manage this
  }
}

#------------------------------------------------------------------------------
# Auto Scaling Configuration - Application Auto Scaling
#------------------------------------------------------------------------------
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = var.max_capacity
  min_capacity       = var.desired_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.rung.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_policy_cpu" {
  name               = "${local.name_prefix}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

resource "aws_appautoscaling_policy" "ecs_policy_memory" {
  name               = "${local.name_prefix}-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 80.0
  }
}

#------------------------------------------------------------------------------
# Security Group - ECS Tasks
#------------------------------------------------------------------------------
resource "aws_security_group" "ecs" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "Security group for Rung ECS tasks"
  vpc_id      = var.vpc_id

  # Inbound from ALB
  ingress {
    description     = "HTTP from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  # Outbound to RDS
  egress {
    description     = "PostgreSQL to RDS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.rds_security_group_id]
  }

  # Outbound to S3 via VPC endpoint
  egress {
    description     = "HTTPS to S3 VPC endpoint"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    prefix_list_ids = [var.s3_vpc_endpoint_prefix_list_id]
  }

  # Outbound to Bedrock via VPC endpoint
  egress {
    description     = "HTTPS to Bedrock VPC endpoint"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [var.vpc_endpoints_security_group_id]
  }

  # Outbound to external services via NAT (Perplexity, etc.)
  egress {
    description = "HTTPS to external services via NAT"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound DNS
  egress {
    description = "DNS resolution"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-sg"
  })
}

#------------------------------------------------------------------------------
# ALB Listener Rule - Route traffic to Rung
#------------------------------------------------------------------------------
resource "aws_lb_listener" "rung" {
  load_balancer_arn = var.alb_arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.rung.arn
  }

  depends_on = [aws_lb_target_group.rung]
}

#------------------------------------------------------------------------------
# CloudWatch Alarms - Service Health Monitoring
#------------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  alarm_name          = "${local.name_prefix}-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS task CPU utilization is above 80%"

  dimensions = {
    ServiceName = aws_ecs_service.rung.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory" {
  alarm_name          = "${local.name_prefix}-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "ECS task memory utilization is above 85%"

  dimensions = {
    ServiceName = aws_ecs_service.rung.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "alb_target_health" {
  alarm_name          = "${local.name_prefix}-unhealthy-targets"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "ALB has unhealthy targets"

  dimensions = {
    TargetGroup  = aws_lb_target_group.rung.name
    LoadBalancer = regex("loadbalancer/(.*)", var.alb_arn)[0]
  }

  tags = local.common_tags
}

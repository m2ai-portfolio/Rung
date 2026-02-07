# Rung Deployment Infrastructure Guide

This document describes the deployment infrastructure created for Rung - a HIPAA-compliant psychology agent orchestration system.

## Overview

The deployment infrastructure consists of:
- **Docker**: Multi-stage containerization with security best practices
- **ECS Fargate**: Serverless container orchestration on AWS
- **Terraform**: Infrastructure as Code with HIPAA compliance
- **CI/CD Pipeline**: Makefile-based deployment automation

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Application Load Balancer (Public Subnet)           │
│ - HTTPS termination (via ALB)                       │
│ - Health checks on /health                          │
└──────────────────────┬──────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────┐
│ ECS Service (Private Subnet)                        │
│ - Fargate Launch Type                               │
│ - Auto-scaling: 1-3 instances                       │
│ - CloudWatch Container Logs (encrypted)             │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
    ┌────────┐   ┌─────────┐   ┌──────────┐
    │  RDS   │   │   S3    │   │ Bedrock  │
    │PostgreSQL   │(Encrypted)  │(VPC EP)  │
    │(Encrypted)  └─────────┘   └──────────┘
    └────────┘
```

## Files Created

### 1. Docker Image (`/home/ubuntu/projects/Rung/Dockerfile`)

Multi-stage Dockerfile with security best practices:
- **Stage 1**: Python 3.12 slim with pip dependencies (builder)
- **Stage 2**: Minimal runtime with non-root user (rung)
- **Health Checks**: `/health` endpoint for load balancer integration
- **No Root User**: Runs as unprivileged `rung` user
- **Small Image Size**: Slim base image + single-stage copy

Build command:
```bash
docker build -t rung:latest .
```

### 2. FastAPI Application Entry Point (`/home/ubuntu/projects/Rung/src/api/app.py`)

Main FastAPI application that:
- Initializes the FastAPI app with metadata
- Provides `/health` and `/healthz` endpoints
- Includes all API routers dynamically
- Handles validation errors gracefully
- Supports environment-based configuration (dev/production)
- No documentation endpoints in production (`RUNG_ENV=production`)

### 3. ECS Terraform Module (`/home/ubuntu/projects/Rung/terraform/modules/ecs/`)

Complete Fargate infrastructure module with:

#### `main.tf` (~350 lines)
- **ECR Repository**: Image storage with vulnerability scanning
- **ECS Cluster**: CloudWatch Container Insights enabled
- **ECS Task Definition**: 512 CPU / 1024 MB memory (configurable)
- **ECS Service**: Fargate with health checks and circuit breaker
- **ALB Target Group**: HTTP health checks on `/health`
- **Auto Scaling**: CPU (70%) and Memory (80%) based scaling
- **CloudWatch Logs**: Encrypted with KMS
- **CloudWatch Alarms**: CPU, memory, and target health monitoring
- **Security Group**: Secure egress to RDS, S3, Bedrock, external services

#### `iam.tf` (~120 lines)
- **Task Execution Role**: Pull ECR images, write logs, read secrets
- **Task Role**: Application permissions for AWS services:
  - Bedrock (Claude model invocation)
  - Transcribe Medical (voice processing)
  - S3 (read voice files and documents)
  - RDS (database access)
  - KMS (encryption/decryption)
  - CloudWatch Metrics (custom metrics)

#### `variables.tf` (~150 lines)
Variables for container configuration, network settings, database, KMS keys, S3 bucket, and logging.

#### `outputs.tf` (~80 lines)
Exports for ECR URL, ECS cluster/service names, task definition, target group, logs, and IAM role ARNs.

### 4. Development Environment Configuration (`/home/ubuntu/projects/Rung/terraform/environments/dev/ecs.tf`)

Integrates ECS module into the dev environment:
- Creates Application Load Balancer
- Configures ECS with dev-appropriate sizing (1 desired, max 3)
- Links to existing VPC, RDS, KMS, and S3 modules
- Exports ALB DNS name and ECS details

### 5. Makefile (`/home/ubuntu/projects/Rung/Makefile`)

Comprehensive development and deployment commands:

**Development:**
```bash
make dev              # Start FastAPI dev server with auto-reload
make test             # Run tests with coverage
make lint             # Run ruff + mypy
make fmt              # Format code (Black, isort, Prettier)
make migrate          # Run Alembic migrations
```

**Docker & Deployment:**
```bash
make build            # Build Docker image
make run-local        # Run container locally
make push             # Build and push to ECR
make deploy           # Deploy to ECS (force new deployment)
make deployment-status # Check ECS service status
make logs             # Follow CloudWatch logs
```

**Infrastructure:**
```bash
make tf-plan          # Terraform plan
make tf-apply         # Terraform apply (interactive confirmation)
make tf-validate      # Validate Terraform syntax
make tf-fmt           # Format Terraform files
make tf-output        # Show outputs
```

## Deployment Workflow

### 1. First Time Setup

Initialize Terraform:
```bash
cd terraform/environments/dev
terraform init
terraform validate
```

Apply infrastructure:
```bash
make tf-apply
```

This creates:
- ECR repository
- ECS cluster and service
- Application Load Balancer
- CloudWatch log group
- IAM roles for ECS tasks

### 2. Build and Deploy

Build Docker image:
```bash
make build
```

Push to ECR:
```bash
make push
```

This will:
1. Authenticate with ECR
2. Tag the image with ECR repository URL
3. Push to ECR with `:latest` tag

Deploy to ECS:
```bash
make deploy
```

This will:
1. Force a new ECS service deployment
2. Pull the latest image from ECR
3. Start new containers
4. Update load balancer target group
5. Perform health checks

Check deployment status:
```bash
make deployment-status
make logs
```

### 3. Running Locally

For local development/testing:
```bash
make run-local
```

This requires:
- `.env` file with `DATABASE_URL`, API keys, etc.
- Docker installed locally

## HIPAA Compliance Features

### Encryption
- **RDS**: Encrypted at rest with KMS
- **S3**: Encrypted with KMS
- **ECR**: Encrypted with KMS
- **CloudWatch Logs**: Encrypted with KMS
- **Transit**: VPC Endpoints for AWS services (no internet exposure)

### Network Security
- **Private Subnets**: ECS tasks run in private subnets
- **Security Groups**: Restrictive rules for ingress/egress
- **VPC Endpoints**: S3 and Bedrock accessed via VPC endpoints (no NAT needed)
- **ALB**: In public subnet, shields ECS from direct internet access

### Audit & Monitoring
- **CloudWatch Logs**: All container logs encrypted and retained 365 days
- **CloudWatch Alarms**: CPU, memory, and health monitoring
- **VPC Flow Logs**: Network traffic logging (365 day retention)
- **IAM Roles**: Least privilege access for tasks

### Configuration Management
- **Secrets Manager**: Database credentials encrypted and rotated
- **Environment Variables**: Non-sensitive config passed at runtime
- **No Hardcoded Secrets**: All sensitive data via Secrets Manager

## Container Image Details

### Base Image
- `python:3.12-slim` (security-patched, minimal)
- ~150MB base size

### Security Hardening
- **Non-root user**: Runs as `rung:rung` (UID/GID 1000+)
- **Multi-stage build**: Only runtime dependencies in final image
- **Health check**: Built-in health check (30s interval, 10s startup grace)
- **Read-only root filesystem**: Can be enabled in production

### Runtime Environment
- **Port**: 8000 (HTTP)
- **Workers**: 2 Uvicorn workers
- **Startup**: ~5 seconds
- **Memory**: 1024 MB (configurable)

## Auto-Scaling Configuration

### CPU-Based Scaling
- Target: 70% CPU utilization
- Scales up/down automatically

### Memory-Based Scaling
- Target: 80% memory utilization
- Scales up/down automatically

### Deployment Circuit Breaker
- Automatic rollback on task failures
- Preserves previous stable task definition

## Monitoring & Alerts

CloudWatch Alarms trigger on:
1. **CPU > 80%**: Scaling adjustment needed
2. **Memory > 85%**: Potential memory leak
3. **Unhealthy targets**: Service unavailable

Action: Send to SNS topic (configure in AWS console)

## Cost Optimization

### Dev Environment
- 1 task normally, max 3 (cost-effective)
- 512 CPU / 1024 MB memory (small)
- Auto-scaling handles traffic spikes

### Production Recommendations
- 2+ minimum tasks (high availability)
- 1024+ CPU / 2048+ MB memory (depends on load)
- Reserved Capacity: 30-50% savings
- Spot instances: For non-critical workloads

## Troubleshooting

### Service Won't Start
1. Check CloudWatch logs: `make logs`
2. Verify IAM role permissions
3. Check health check endpoint: `curl http://alb-dns:8000/health`

### Deployment Stuck
1. Check ECS service events in AWS console
2. Verify image exists in ECR: `aws ecr describe-images --repository-name rung-dev`
3. Check task definition: `make tf-output | grep task_definition`

### Performance Issues
1. Check auto-scaling metrics: `make deployment-status`
2. Review CloudWatch logs for errors
3. Increase CPU/memory if consistently high utilization

### Database Connection Issues
1. Verify security group allows ECS→RDS (5432)
2. Check database secret in Secrets Manager
3. Ensure RDS is in same VPC as ECS

## Next Steps

### For Production
1. Enable HTTPS on ALB (ACM certificate)
2. Configure Route53 for domain
3. Set up Cognito authentication (already configured)
4. Enable deletion protection on RDS
5. Set up CloudTrail for audit logging
6. Configure SNS for alarms

### For CI/CD
1. Create GitHub Actions workflow for automated deployments
2. Add security scanning (container, dependencies)
3. Add integration tests before deployment
4. Set up blue-green deployments

### For Observability
1. Add APM integration (e.g., X-Ray, New Relic)
2. Configure distributed tracing
3. Set up custom CloudWatch dashboards
4. Add cost monitoring

## References

- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-networking.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [HIPAA Security Requirements](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)

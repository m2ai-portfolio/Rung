.PHONY: help build push deploy test lint fmt dev migrate tf-plan tf-apply tf-validate

# Variables
IMAGE_NAME ?= rung
AWS_REGION ?= us-east-1
TERRAFORM_DIR ?= terraform/environments/dev
PYTHON_FILES := src tests

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)Rung Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make dev              - Start FastAPI dev server with auto-reload"
	@echo "  make test             - Run test suite with coverage"
	@echo "  make lint             - Run linters (ruff, mypy)"
	@echo "  make fmt              - Format code (Black, isort, Prettier)"
	@echo "  make migrate          - Run database migrations"
	@echo "  make migrate-check    - Check migration status"
	@echo ""
	@echo "$(GREEN)Docker & Deployment:$(NC)"
	@echo "  make build            - Build Docker image locally"
	@echo "  make run-local        - Run container locally with .env"
	@echo "  make push             - Build and push to ECR"
	@echo "  make deploy           - Deploy to ECS (requires push)"
	@echo ""
	@echo "$(GREEN)Infrastructure:$(NC)"
	@echo "  make tf-plan          - Terraform plan (dev environment)"
	@echo "  make tf-apply         - Terraform apply (dev environment)"
	@echo "  make tf-validate      - Validate Terraform syntax"
	@echo ""

# =============================================================================
# Development
# =============================================================================

dev:
	@echo "$(BLUE)Starting FastAPI dev server...$(NC)"
	uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing --tb=short
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(NC)"

test-quick:
	@echo "$(BLUE)Running quick tests...$(NC)"
	python -m pytest tests/ -v --tb=short -x

lint:
	@echo "$(BLUE)Running linters...$(NC)"
	ruff check $(PYTHON_FILES) --show-fixes
	mypy src/ --ignore-missing-imports --show-error-codes
	@echo "$(GREEN)Linting complete$(NC)"

fmt:
	@echo "$(BLUE)Formatting code...$(NC)"
	black $(PYTHON_FILES)
	isort $(PYTHON_FILES)
	prettier --write . --ignore-path .gitignore
	@echo "$(GREEN)Code formatted$(NC)"

fmt-check:
	@echo "$(BLUE)Checking code formatting...$(NC)"
	black --check $(PYTHON_FILES)
	isort --check-only $(PYTHON_FILES)
	@echo "$(GREEN)Format check passed$(NC)"

# =============================================================================
# Docker - Build and Push
# =============================================================================

build:
	@echo "$(BLUE)Building Docker image: $(IMAGE_NAME):latest$(NC)"
	docker build -t $(IMAGE_NAME):latest .
	@echo "$(GREEN)Docker image built successfully$(NC)"

build-with-cache:
	@echo "$(BLUE)Building Docker image with cache: $(IMAGE_NAME):latest$(NC)"
	docker build --progress=plain -t $(IMAGE_NAME):latest .

run-local: build
	@echo "$(BLUE)Running container locally...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)Error: .env file not found. Create it using .env.example$(NC)"; \
		exit 1; \
	fi
	docker run -p 8000:8000 --env-file .env $(IMAGE_NAME):latest

push: build
	@echo "$(BLUE)Pushing to ECR...$(NC)"
	$(eval ECR_REPO = $(shell terraform -chdir=$(TERRAFORM_DIR) output -raw ecr_repository_url 2>/dev/null || echo "NOT_SET"))
	@if [ "$(ECR_REPO)" = "NOT_SET" ]; then \
		echo "$(RED)Error: ECR repository not found. Run 'make tf-apply' first.$(NC)"; \
		exit 1; \
	fi
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPO)
	docker tag $(IMAGE_NAME):latest $(ECR_REPO):latest
	docker push $(ECR_REPO):latest
	@echo "$(GREEN)Image pushed to ECR$(NC)"

# =============================================================================
# Deployment
# =============================================================================

deploy: push
	@echo "$(BLUE)Deploying to ECS...$(NC)"
	$(eval CLUSTER_NAME = $(shell terraform -chdir=$(TERRAFORM_DIR) output -raw ecs_cluster_name 2>/dev/null || echo "NOT_SET"))
	$(eval SERVICE_NAME = $(shell terraform -chdir=$(TERRAFORM_DIR) output -raw ecs_service_name 2>/dev/null || echo "NOT_SET"))
	@if [ "$(CLUSTER_NAME)" = "NOT_SET" ] || [ "$(SERVICE_NAME)" = "NOT_SET" ]; then \
		echo "$(RED)Error: ECS cluster/service not found. Run 'make tf-apply' first.$(NC)"; \
		exit 1; \
	fi
	aws ecs update-service \
		--cluster $(CLUSTER_NAME) \
		--service $(SERVICE_NAME) \
		--force-new-deployment \
		--region $(AWS_REGION)
	@echo "$(GREEN)ECS service update initiated$(NC)"

deployment-status:
	@echo "$(BLUE)Checking deployment status...$(NC)"
	$(eval CLUSTER_NAME = $(shell terraform -chdir=$(TERRAFORM_DIR) output -raw ecs_cluster_name 2>/dev/null))
	$(eval SERVICE_NAME = $(shell terraform -chdir=$(TERRAFORM_DIR) output -raw ecs_service_name 2>/dev/null))
	aws ecs describe-services \
		--cluster $(CLUSTER_NAME) \
		--services $(SERVICE_NAME) \
		--region $(AWS_REGION) \
		--query 'services[0].{Status:status,DesiredCount:desiredCount,RunningCount:runningCount}'

logs:
	@echo "$(BLUE)Fetching recent logs...$(NC)"
	$(eval LOG_GROUP = $(shell terraform -chdir=$(TERRAFORM_DIR) output -raw cloudwatch_log_group 2>/dev/null))
	aws logs tail $(LOG_GROUP) --follow --region $(AWS_REGION)

# =============================================================================
# Database
# =============================================================================

migrate:
	@echo "$(BLUE)Running database migrations...$(NC)"
	PYTHONPATH=. alembic upgrade head
	@echo "$(GREEN)Migrations applied successfully$(NC)"

migrate-check:
	@echo "$(BLUE)Checking migration status...$(NC)"
	PYTHONPATH=. alembic current

migrate-rollback:
	@echo "$(BLUE)Rolling back to previous migration...$(NC)"
	PYTHONPATH=. alembic downgrade -1
	@echo "$(GREEN)Rollback complete$(NC)"

# =============================================================================
# Infrastructure / Terraform
# =============================================================================

tf-plan:
	@echo "$(BLUE)Planning Terraform changes ($(TERRAFORM_DIR))...$(NC)"
	terraform -chdir=$(TERRAFORM_DIR) plan -out=tfplan

tf-apply:
	@echo "$(BLUE)Applying Terraform changes ($(TERRAFORM_DIR))...$(NC)"
	@echo "$(RED)Warning: This will create AWS resources and may incur costs$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		terraform -chdir=$(TERRAFORM_DIR) apply; \
	else \
		echo "$(RED)Terraform apply cancelled$(NC)"; \
	fi

tf-destroy:
	@echo "$(RED)Destroying Terraform infrastructure ($(TERRAFORM_DIR))...$(NC)"
	@echo "$(RED)Warning: This will delete AWS resources$(NC)"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		terraform -chdir=$(TERRAFORM_DIR) destroy; \
	else \
		echo "$(RED)Terraform destroy cancelled$(NC)"; \
	fi

tf-validate:
	@echo "$(BLUE)Validating Terraform syntax...$(NC)"
	terraform -chdir=$(TERRAFORM_DIR) validate
	@echo "$(GREEN)Terraform validation passed$(NC)"

tf-fmt:
	@echo "$(BLUE)Formatting Terraform files...$(NC)"
	terraform -chdir=$(TERRAFORM_DIR) fmt -recursive
	@echo "$(GREEN)Terraform files formatted$(NC)"

tf-output:
	@echo "$(BLUE)Terraform outputs:$(NC)"
	terraform -chdir=$(TERRAFORM_DIR) output

# =============================================================================
# Utility
# =============================================================================

clean:
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/ .mypy_cache/ htmlcov/
	@echo "$(GREEN)Clean complete$(NC)"

requirements-check:
	@echo "$(BLUE)Checking for outdated packages...$(NC)"
	pip list --outdated

requirements-install:
	@echo "$(BLUE)Installing requirements...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)Requirements installed$(NC)"

.env-check:
	@if [ ! -f .env ]; then \
		echo "$(RED)Error: .env file not found$(NC)"; \
		if [ -f .env.example ]; then \
			echo "Creating .env from .env.example..."; \
			cp .env.example .env; \
			echo "$(GREEN).env created - please update with your values$(NC)"; \
		fi; \
		exit 1; \
	fi

# =============================================================================
# Quick Reference
# =============================================================================

.PHONY: all
all: help

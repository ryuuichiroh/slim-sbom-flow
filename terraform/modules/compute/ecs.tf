data "aws_region" "current" {}

locals {
  region         = data.aws_region.current.name
  cognito_issuer = "https://cognito-idp.${local.region}.amazonaws.com/${var.cognito_user_pool_id}"
  database_url   = "jdbc:postgresql://${var.rds_address}:5432/${var.db_name}"
}

# ECS Cluster

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  configuration {
    execute_command_configuration {
      logging = "DEFAULT"
    }
  }

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Project = var.project_name
  }
}

# CloudWatch Log Groups

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project_name}-api-task"
  retention_in_days = var.log_retention_days

  tags = {
    Project = var.project_name
  }
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}-frontend-task"
  retention_in_days = var.log_retention_days

  tags = {
    Project = var.project_name
  }
}

# API Task Definition

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-api-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_api_task_cpu
  memory                   = var.ecs_api_task_memory
  execution_role_arn       = var.ecs_task_execution_role_arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  volume {
    name = "${var.project_name}-dtrack-data"

    efs_volume_configuration {
      file_system_id     = var.efs_id
      root_directory     = "/"
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = var.efs_access_point_id
        iam             = "DISABLED"
      }
    }
  }

  volume {
    name = "${var.project_name}-trivy-cache"

    efs_volume_configuration {
      file_system_id     = var.efs_id
      root_directory     = "/"
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = var.efs_access_point_trivy_id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "${var.project_name}-apiserver"
      image     = var.dependency_track_api_image
      essential = true

      portMappings = [
        {
          name          = "http-api"
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
          appProtocol   = "http"
        }
      ]

      environment = [
        { name = "ALPINE_DATABASE_DRIVER", value = "org.postgresql.Driver" },
        { name = "ALPINE_DATABASE_MODE", value = "external" },
        { name = "ALPINE_DATABASE_URL", value = local.database_url },
        { name = "ALPINE_DATABASE_USERNAME", value = var.db_username },
        { name = "ALPINE_OIDC_ENABLED", value = "true" },
        { name = "ALPINE_OIDC_ISSUER", value = local.cognito_issuer },
        { name = "ALPINE_OIDC_CLIENT_ID", value = var.cognito_client_id },
        { name = "ALPINE_OIDC_USERNAME_CLAIM", value = "email" },
        { name = "ALPINE_OIDC_TEAMS_CLAIM", value = "cognito:groups" },
        { name = "ALPINE_OIDC_USER_PROVISIONING", value = "true" },
        { name = "ALPINE_OIDC_TEAM_SYNCHRONIZATION", value = "true" },
      ]

      secrets = [
        {
          name      = "ALPINE_DATABASE_PASSWORD"
          valueFrom = "${var.secrets_manager_secret_arn}:DB_PASSWORD::"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "${var.project_name}-dtrack-data"
          containerPath = "/data"
          readOnly      = false
        }
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/health/ready || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 5
        startPeriod = 120
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      dependsOn = [
        {
          containerName = "${var.project_name}-trivy"
          condition     = "HEALTHY"
        }
      ]

      dockerLabels = {
        Project = var.project_name
      }
    },
    {
      name      = "${var.project_name}-trivy"
      image     = var.trivy_image
      essential = false
      command   = ["server", "--listen", "0.0.0.0:8082", "--cache-dir", "/cache"]

      portMappings = [
        {
          name          = "trivy"
          containerPort = 8082
          hostPort      = 8082
          protocol      = "tcp"
          appProtocol   = "http"
        }
      ]

      secrets = [
        {
          name      = "TRIVY_TOKEN"
          valueFrom = "${var.secrets_manager_secret_arn}:TRIVY_TOKEN::"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "${var.project_name}-trivy-cache"
          containerPath = "/cache"
          readOnly      = false
        }
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "trivy --version || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      dockerLabels = {
        Project = var.project_name
      }
    }
  ])

  tags = {
    Project = var.project_name
  }
}

# Frontend Task Definition

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_frontend_task_cpu
  memory                   = var.ecs_frontend_task_memory
  execution_role_arn       = var.ecs_task_execution_role_arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "${var.project_name}-frontend"
      image     = var.dependency_track_frontend_image
      essential = true

      portMappings = [
        {
          name          = "http-ui"
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
          appProtocol   = "http"
        }
      ]

      environment = [
        { name = "API_BASE_URL", value = "https://${var.app_domain}" },
        { name = "OIDC_ISSUER", value = local.cognito_issuer },
        { name = "OIDC_CLIENT_ID", value = var.cognito_client_id },
        { name = "OIDC_SCOPE", value = "openid email" },
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      dockerLabels = {
        Project = var.project_name
      }
    }
  ])

  tags = {
    Project = var.project_name
  }
}

# ECS Services

resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api-task-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.ecs_api_desired_count

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 0
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.alb_target_group_api_arn
    container_name   = "${var.project_name}-apiserver"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  health_check_grace_period_seconds  = 120
  enable_ecs_managed_tags            = true

  tags = {
    Project = var.project_name
  }
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend-task-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.ecs_frontend_desired_count

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 0
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.alb_target_group_frontend_arn
    container_name   = "${var.project_name}-frontend"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  health_check_grace_period_seconds  = 30
  enable_ecs_managed_tags            = true

  tags = {
    Project = var.project_name
  }
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "ECS security group ID"
  type        = string
}

variable "alb_target_group_api_arn" {
  description = "ALB target group ARN for API"
  type        = string
}

variable "alb_target_group_frontend_arn" {
  description = "ALB target group ARN for Frontend"
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  type        = string
}

variable "efs_id" {
  description = "EFS file system ID"
  type        = string
}

variable "efs_access_point_id" {
  description = "EFS access point ID"
  type        = string
}

variable "rds_address" {
  description = "RDS instance address (hostname)"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "secrets_manager_secret_arn" {
  description = "Secrets Manager secret ARN"
  type        = string
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "cognito_client_id" {
  description = "Cognito User Pool Client ID"
  type        = string
}

variable "app_domain" {
  description = "Application domain name"
  type        = string
}

variable "dependency_track_api_image" {
  description = "Dependency-Track API image"
  type        = string
}

variable "dependency_track_frontend_image" {
  description = "Dependency-Track frontend image"
  type        = string
}

variable "trivy_image" {
  description = "Trivy image"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
}

variable "ecs_api_task_cpu" {
  description = "CPU units for API task (1024 = 1 vCPU)"
  type        = number
}

variable "ecs_api_task_memory" {
  description = "Memory for API task in MB"
  type        = number
}

variable "ecs_frontend_task_cpu" {
  description = "CPU units for Frontend task (1024 = 1 vCPU)"
  type        = number
}

variable "ecs_frontend_task_memory" {
  description = "Memory for Frontend task in MB"
  type        = number
}

variable "ecs_api_desired_count" {
  description = "Desired number of API task instances"
  type        = number
}

variable "ecs_frontend_desired_count" {
  description = "Desired number of Frontend task instances"
  type        = number
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

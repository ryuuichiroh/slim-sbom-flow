variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "ssf"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "aws_profile" {
  description = "AWS CLI profile name"
  type        = string
  default     = "ssf"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones for multi-AZ deployment"
  type        = list(string)
  default     = ["ap-northeast-1a", "ap-northeast-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.0.0/20", "10.0.16.0/20"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.128.0/20", "10.0.144.0/20"]
}

variable "office_ip_cidr" {
  description = "Office IP address range for ALB access control"
  type        = string
  default     = "0.0.0.0/0"
}

variable "app_domain" {
  description = "Application domain name (e.g. ssf.example.com)"
  type        = string
}

variable "cognito_domain" {
  description = "Cognito user pool domain prefix"
  type        = string
  default     = "ssf-dt"
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for ALB HTTPS listener"
  type        = string
}

variable "db_name" {
  description = "RDS database name"
  type        = string
  default     = "dtrack"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "dtrack"
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for RDS (recommended for production)"
  type        = bool
  default     = false
}

variable "db_allocated_storage" {
  description = "Initial storage size for RDS in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum storage size for RDS auto-scaling in GB"
  type        = number
  default     = 1000
}

variable "db_backup_retention_period" {
  description = "Number of days to retain automated backups (0 = disabled)"
  type        = number
  default     = 0
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for RDS and ALB (recommended for production)"
  type        = bool
  default     = false
}

variable "enable_efs_backup" {
  description = "Enable automatic backups for EFS (recommended for production)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 30
}

variable "ecs_api_task_cpu" {
  description = "CPU units for API task (1024 = 1 vCPU)"
  type        = number
  default     = 2048
}

variable "ecs_api_task_memory" {
  description = "Memory for API task in MB"
  type        = number
  default     = 8192
}

variable "ecs_frontend_task_cpu" {
  description = "CPU units for Frontend task (1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "ecs_frontend_task_memory" {
  description = "Memory for Frontend task in MB"
  type        = number
  default     = 512
}

variable "ecs_api_desired_count" {
  description = "Desired number of API task instances"
  type        = number
  default     = 1
}

variable "ecs_frontend_desired_count" {
  description = "Desired number of Frontend task instances"
  type        = number
  default     = 1
}

variable "dependency_track_api_image" {
  description = "Dependency-Track API Server container image"
  type        = string
  default     = "dependencytrack/apiserver:latest"
}

variable "dependency_track_frontend_image" {
  description = "Dependency-Track Frontend container image"
  type        = string
  default     = "dependencytrack/frontend:latest"
}

variable "trivy_image" {
  description = "Trivy scanner container image"
  type        = string
  default     = "public.ecr.aws/aquasecurity/trivy:latest"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "ssf"
    ManagedBy   = "Terraform"
    Environment = "production"
  }
}

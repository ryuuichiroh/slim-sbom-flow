variable "project_name" {
  description = "Project name"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs"
  type        = list(string)
}

variable "rds_security_group_id" {
  description = "RDS security group ID"
  type        = string
}

variable "efs_security_group_id" {
  description = "EFS security group ID"
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

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for RDS"
  type        = bool
}

variable "db_allocated_storage" {
  description = "Initial storage size for RDS in GB"
  type        = number
}

variable "db_max_allocated_storage" {
  description = "Maximum storage size for RDS auto-scaling in GB"
  type        = number
}

variable "db_backup_retention_period" {
  description = "Number of days to retain automated backups"
  type        = number
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for RDS"
  type        = bool
}

variable "enable_efs_backup" {
  description = "Enable automatic backups for EFS"
  type        = bool
}

variable "secrets_manager_secret_id" {
  description = "Secrets Manager secret ID for database credentials"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block (for EFS/RDS security group ingress)"
  type        = string
}

variable "app_domain" {
  description = "Application domain name for Cognito callback URLs"
  type        = string
}

variable "cognito_domain" {
  description = "Cognito user pool domain prefix"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

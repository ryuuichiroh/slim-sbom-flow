output "vpc_id" {
  description = "VPC ID"
  value       = module.network.vpc_id
}

output "alb_dns_name" {
  description = "ALB DNS name - use this to configure your DNS"
  value       = module.routing.alb_dns_name
}

output "alb_arn" {
  description = "ALB ARN"
  value       = module.routing.alb_arn
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.data.rds_endpoint
  sensitive   = true
}

output "efs_id" {
  description = "EFS file system ID"
  value       = module.data.efs_id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.compute.ecs_cluster_name
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID"
  value       = module.security.cognito_user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito user pool client ID"
  value       = module.security.cognito_user_pool_client_id
}

output "gha_custom_header" {
  description = "GitHub Actions custom header for API authentication (use this in GitHub Actions secrets)"
  value       = module.data.gha_custom_header
  sensitive   = true
}

output "next_steps" {
  description = "Next steps after deployment"
  sensitive   = true
  value       = <<-EOT

  === Deployment Completed ===

  1. Configure DNS:
     - Create A record pointing to: ${module.routing.alb_dns_name}

  2. Access Dependency-Track:
     - URL: https://${var.app_domain}

  3. Configure Cognito:
     - User Pool ID: ${module.security.cognito_user_pool_id}
     - Client ID: ${module.security.cognito_user_pool_client_id}

  4. Database connection:
     - Use terraform output rds_endpoint to get the endpoint
     - Database: ${var.db_name}
     - Username: ${var.db_username}

  5. ECS Cluster:
     - Name: ${module.compute.ecs_cluster_name}
     - API Service: ${module.compute.ecs_service_api_name}
     - Frontend Service: ${module.compute.ecs_service_frontend_name}

  EOT
}

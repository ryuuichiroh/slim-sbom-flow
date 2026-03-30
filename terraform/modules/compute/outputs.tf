output "ecs_cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_api_name" {
  description = "API service name"
  value       = aws_ecs_service.api.name
}

output "ecs_service_frontend_name" {
  description = "Frontend service name"
  value       = aws_ecs_service.frontend.name
}

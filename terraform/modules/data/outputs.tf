output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "RDS address"
  value       = aws_db_instance.main.address
}

output "efs_id" {
  description = "EFS file system ID"
  value       = aws_efs_file_system.main.id
}

output "efs_access_point_id" {
  description = "EFS access point ID"
  value       = aws_efs_access_point.main.id
}

output "gha_custom_header" {
  description = "GitHub Actions custom header for ALB authentication"
  value       = random_password.gha_custom_header.result
  sensitive   = true
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.main.arn
}

output "alb_target_group_api_arn" {
  description = "API target group ARN"
  value       = aws_lb_target_group.api.arn
}

output "alb_target_group_frontend_arn" {
  description = "Frontend target group ARN"
  value       = aws_lb_target_group.frontend.arn
}

resource "aws_secretsmanager_secret" "credentials" {
  name        = "${var.project_name}/credentials"
  description = "Credentials for ${var.project_name}"

  tags = {
    Project = var.project_name
  }
}

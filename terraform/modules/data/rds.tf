resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-db-subnet-group"
  description = "DB subnet group for ${var.project_name}"
  subnet_ids  = concat(var.private_subnet_ids, var.public_subnet_ids)
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "17.6"
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_security_group_id]
  publicly_accessible    = false
  multi_az               = var.db_multi_az
  port                   = 5432

  backup_retention_period = var.db_backup_retention_period
  copy_tags_to_snapshot   = true
  deletion_protection     = var.enable_deletion_protection
  skip_final_snapshot     = true

  auto_minor_version_upgrade          = true
  performance_insights_enabled        = false
  iam_database_authentication_enabled = false

  tags = {
    Project = var.project_name
  }

  lifecycle {
    ignore_changes = [password]
  }
}

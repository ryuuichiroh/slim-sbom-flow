resource "aws_efs_file_system" "main" {
  encrypted        = true
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name    = "${var.project_name}-efs"
    Project = var.project_name
  }
}

resource "aws_efs_backup_policy" "main" {
  file_system_id = aws_efs_file_system.main.id

  backup_policy {
    status = var.enable_efs_backup ? "ENABLED" : "DISABLED"
  }
}

resource "aws_efs_access_point" "main" {
  file_system_id = aws_efs_file_system.main.id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/dtrack"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }

  tags = {
    Name    = "${var.project_name}-efs-ap-dtrack"
    Project = var.project_name
  }
}

resource "aws_efs_access_point" "trivy" {
  file_system_id = aws_efs_file_system.main.id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/trivy-cache"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }

  tags = {
    Name    = "${var.project_name}-efs-ap-trivy"
    Project = var.project_name
  }
}

resource "aws_efs_mount_target" "private_1a" {
  file_system_id  = aws_efs_file_system.main.id
  subnet_id       = var.private_subnet_ids[0]
  security_groups = [var.efs_security_group_id]
}

resource "aws_efs_mount_target" "private_1c" {
  file_system_id  = aws_efs_file_system.main.id
  subnet_id       = var.private_subnet_ids[1]
  security_groups = [var.efs_security_group_id]
}

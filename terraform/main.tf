module "network" {
  source = "./modules/network"

  project_name         = var.project_name
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  tags                 = var.tags
}

module "security" {
  source = "./modules/security"

  project_name   = var.project_name
  vpc_id         = module.network.vpc_id
  vpc_cidr       = var.vpc_cidr
  app_domain     = var.app_domain
  cognito_domain = var.cognito_domain
  tags           = var.tags
}

module "data" {
  source = "./modules/data"

  project_name               = var.project_name
  private_subnet_ids         = module.network.private_subnet_ids
  public_subnet_ids          = module.network.public_subnet_ids
  rds_security_group_id      = module.security.rds_security_group_id
  efs_security_group_id      = module.security.efs_security_group_id
  secrets_manager_secret_id  = module.security.secrets_manager_secret_id
  db_name                    = var.db_name
  db_username                = var.db_username
  db_instance_class          = var.db_instance_class
  db_multi_az                = var.db_multi_az
  db_allocated_storage       = var.db_allocated_storage
  db_max_allocated_storage   = var.db_max_allocated_storage
  db_backup_retention_period = var.db_backup_retention_period
  enable_deletion_protection = var.enable_deletion_protection
  enable_efs_backup          = var.enable_efs_backup
  tags                       = var.tags
}

module "routing" {
  source = "./modules/routing"

  project_name               = var.project_name
  vpc_id                     = module.network.vpc_id
  public_subnet_ids          = module.network.public_subnet_ids
  alb_security_group_id      = module.security.alb_security_group_id
  acm_certificate_arn        = var.acm_certificate_arn
  office_ip_cidr             = var.office_ip_cidr
  gha_custom_header          = module.data.gha_custom_header
  enable_deletion_protection = var.enable_deletion_protection
  tags                       = var.tags
}

module "compute" {
  source = "./modules/compute"

  project_name                    = var.project_name
  private_subnet_ids              = module.network.private_subnet_ids
  ecs_security_group_id           = module.security.ecs_security_group_id
  alb_target_group_api_arn        = module.routing.alb_target_group_api_arn
  alb_target_group_frontend_arn   = module.routing.alb_target_group_frontend_arn
  ecs_task_execution_role_arn     = module.security.ecs_task_execution_role_arn
  efs_id                          = module.data.efs_id
  efs_access_point_id             = module.data.efs_access_point_id
  efs_access_point_trivy_id       = module.data.efs_access_point_trivy_id
  rds_address                     = module.data.rds_address
  db_name                         = var.db_name
  db_username                     = var.db_username
  secrets_manager_secret_arn      = module.security.secrets_manager_secret_arn
  cognito_user_pool_id            = module.security.cognito_user_pool_id
  cognito_client_id               = module.security.cognito_user_pool_client_id
  app_domain                      = var.app_domain
  dependency_track_api_image      = var.dependency_track_api_image
  dependency_track_frontend_image = var.dependency_track_frontend_image
  trivy_image                     = var.trivy_image
  log_retention_days              = var.log_retention_days
  ecs_api_task_cpu                = var.ecs_api_task_cpu
  ecs_api_task_memory             = var.ecs_api_task_memory
  ecs_frontend_task_cpu           = var.ecs_frontend_task_cpu
  ecs_frontend_task_memory        = var.ecs_frontend_task_memory
  ecs_api_desired_count           = var.ecs_api_desired_count
  ecs_frontend_desired_count      = var.ecs_frontend_desired_count
  tags                            = var.tags
}

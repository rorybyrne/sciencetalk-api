# Science Talk - Lightsail Managed PostgreSQL Database

resource "aws_lightsail_database" "main" {
  relational_database_name = "${var.project_name}-db"

  # Instance configuration
  bundle_id    = var.db_bundle_id
  blueprint_id = "postgres_17" # Latest PostgreSQL version

  # Database credentials
  master_database_name = var.db_name
  master_username      = var.db_username
  master_password      = random_password.db_password.result # Auto-generated in secrets.tf

  # Public access required for Lightsail container connectivity
  publicly_accessible = true

  # Backup configuration
  backup_retention_enabled     = true
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"

  # Important: Create final snapshot before deletion
  skip_final_snapshot = false
  final_snapshot_name = "${var.project_name}-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = {
    Name    = "${var.project_name}-database"
    Project = var.project_display_name
  }

  lifecycle {
    ignore_changes = [final_snapshot_name]
  }
}

# Store database connection info in SSM for reference
resource "aws_ssm_parameter" "database_host" {
  name        = "/${var.project_name}/database-host"
  description = "Database endpoint hostname"
  type        = "String"
  value       = aws_lightsail_database.main.master_endpoint_address

  tags = {
    Name = "${var.project_name}-db-host"
  }
}

resource "aws_ssm_parameter" "database_port" {
  name        = "/${var.project_name}/database-port"
  description = "Database endpoint port"
  type        = "String"
  value       = tostring(aws_lightsail_database.main.master_endpoint_port)

  tags = {
    Name = "${var.project_name}-db-port"
  }
}

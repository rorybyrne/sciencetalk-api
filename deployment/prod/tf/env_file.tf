# Science Talk - Environment File Generation
#
# This file configures automatic .env generation from Terraform outputs.
# The .env file merges:
#   - Dynamic values from Terraform (database URL, secrets)
#   - Static values from .env.base (invitations, feature flags, etc.)
#   - Secret values from .env.secret (API tokens, optional)

# Generate .env file automatically
resource "local_file" "env" {
  filename = "${path.module}/../.env"

  content = templatefile("${path.module}/templates/env.tftpl", {
    # Database configuration
    database_url = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_lightsail_database.main.master_endpoint_address}:${aws_lightsail_database.main.master_endpoint_port}/${var.db_name}"

    # Authentication
    jwt_secret = random_password.jwt_secret.result

    api_host = "${var.subdomain}.${var.domain_name}"
    frontend_host = "${var.frontend_subdomain}.${var.domain_name}"

    # AWS Configuration (for GitHub Actions)
    aws_region        = var.aws_region
    lightsail_service = var.project_name
    custom_domain     = "${var.subdomain}.${var.domain_name}"
    certificate_name  = "${var.project_name}-cert"

    # Static configuration from .env.base
    env_base_content = file("${path.module}/../.env.base")

    # Secret configuration from .env.secret (if exists)
    env_secret_content = fileexists("${path.module}/../.env.secret") ? file("${path.module}/../.env.secret") : ""
  })

  # Ensure file has restrictive permissions (readable only by owner)
  file_permission = "0600"

  # This file contains secrets, so it's sensitive
  lifecycle {
    # Prevent accidental deletion
    prevent_destroy = false
  }
}

# Output the env file path for convenience
output "env_file_path" {
  description = "Path to generated .env file"
  value       = local_file.env.filename
}

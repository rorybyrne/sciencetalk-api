# Science Talk - Lightsail Container Service

resource "aws_lightsail_container_service" "main" {
  name  = var.project_name
  power = var.container_power # micro = 0.5 vCPU, 1GB RAM, $10/month
  scale = var.container_scale # Number of container instances

  # Enable ECR access for future use
  private_registry_access {
    ecr_image_puller_role {
      is_active = true
    }
  }

  tags = {
    Name    = "${var.project_name}-container"
    Project = var.project_display_name
  }
}

# SSL/TLS Certificate for custom domain
resource "aws_lightsail_certificate" "main" {
  name        = "${var.project_name}-cert"
  domain_name = "${var.subdomain}.${var.domain_name}"

  # No subject alternative names needed for single domain
  subject_alternative_names = []

  tags = {
    Name = "${var.project_name}-cert"
  }
}

# Note: Container deployment is handled by GitHub Actions CI/CD
# Do not create aws_lightsail_container_service_deployment_version here
# See .github/workflows/deploy.yml for deployment configuration

# Science Talk - Secrets Management
#
# All secrets are generated automatically by Terraform using the random provider.
# Secrets are stored in Terraform state - ensure state file is protected!
#
# Benefits:
# - No manual secret generation required
# - Guaranteed strong, random secrets
# - Consistent secret management
# - Free (no AWS Secrets Manager costs)
#
# Security Note:
# - terraform.tfstate contains secrets in plaintext
# - Never commit state file to git (already in .gitignore)
# - Consider S3 backend with encryption for team environments

# Generate secure JWT secret for application authentication
resource "random_password" "jwt_secret" {
  length  = 64
  special = true

  # Preserve value across runs (don't regenerate on every apply)
  lifecycle {
    ignore_changes = all
  }
}

# Generate secure database password
resource "random_password" "db_password" {
  length  = 32
  special = false

  # Preserve value across runs (don't regenerate on every apply)
  lifecycle {
    ignore_changes = all
  }
}

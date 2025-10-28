# Science Talk - Terraform Outputs

output "container_service_url" {
  description = "Default Lightsail container URL"
  value       = aws_lightsail_container_service.main.url
}

output "website_url" {
  description = "Public URL"
  value       = "https://${var.subdomain}.${var.domain_name}"
}

output "database_endpoint" {
  description = "Database connection endpoint"
  value       = "${aws_lightsail_database.main.master_endpoint_address}:${aws_lightsail_database.main.master_endpoint_port}"
  sensitive   = true
}

output "database_url" {
  description = "Full database connection URL (for DATABASE__URL env var)"
  value       = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_lightsail_database.main.master_endpoint_address}:${aws_lightsail_database.main.master_endpoint_port}/${var.db_name}"
  sensitive   = true
}

output "lightsail_nameservers" {
  description = "Nameservers to configure at your domain registrar"
  value       = "Check Lightsail Console → Networking → DNS zones → ${var.domain_name}"
}

output "jwt_secret" {
  description = "JWT secret for application (add to GitHub Secrets)"
  value       = random_password.jwt_secret.result
  sensitive   = true
}

output "cicd_access_key_id" {
  description = "AWS Access Key ID for CI/CD user (add to GitHub Secrets as AWS_ACCESS_KEY_ID)"
  value       = aws_iam_access_key.cicd.id
  sensitive   = true
}

output "cicd_secret_access_key" {
  description = "AWS Secret Access Key for CI/CD user (add to GitHub Secrets as AWS_SECRET_ACCESS_KEY)"
  value       = aws_iam_access_key.cicd.secret
  sensitive   = true
}

output "env_file_content" {
  description = "Complete .env file content (generated automatically)"
  value = templatefile("${path.module}/templates/env.tftpl", {
    # Database configuration
    database_url = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_lightsail_database.main.master_endpoint_address}:${aws_lightsail_database.main.master_endpoint_port}/${var.db_name}"

    # Authentication
    jwt_secret = random_password.jwt_secret.result

    # API URLs
    api_base_url     = "https://${var.subdomain}.${var.domain_name}"
    api_frontend_url = "https://talk.${var.domain_name}"

    # Environment
    environment = "production"
    debug       = "false"

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
  sensitive = true
}

output "next_steps" {
  description = "Post-deployment instructions"
  value       = <<-EOT
    ═══════════════════════════════════════════════════════════════════════════
    ✅ Terraform Infrastructure Created Successfully!
    ═══════════════════════════════════════════════════════════════════════════

    📋 NEXT STEPS:

    1️⃣  UPDATE DOMAIN NAMESERVERS
        Go to Lightsail Console → Networking → DNS zones → ${var.domain_name}
        Copy the 4 nameservers and configure them at your domain registrar

        ⏱  DNS propagation can take 24-48 hours

    2️⃣  CHECK GENERATED .ENV FILE
        Terraform has automatically generated .env with all configuration:

        cat ../.env

        This file contains:
        ✅ Database URL (from Lightsail PostgreSQL)
        ✅ JWT Secret (randomly generated)
        ✅ API URLs (from your domain configuration)

    3️⃣  CONFIGURE GITHUB SECRETS
        Add these 3 secrets to your GitHub repository:
        Settings → Secrets and variables → Actions → New repository secret

        1. ENV_FILE
           Copy entire .env file: cat ../.env | pbcopy

        2. AWS_ACCESS_KEY_ID
           terraform output -raw cicd_access_key_id | pbcopy

        3. AWS_SECRET_ACCESS_KEY
           terraform output -raw cicd_secret_access_key | pbcopy

        ⚠️  These credentials are for a dedicated CI/CD user with minimal permissions

    4️⃣  DEPLOY VIA GITHUB ACTIONS
        Push to main branch to trigger deployment:

        git push origin main

        Or manually trigger workflow:
        GitHub → Actions → Deploy to AWS Lightsail → Run workflow

    5️⃣  VERIFY DEPLOYMENT
        After deployment completes:

        curl https://${var.subdomain}.${var.domain_name}/health

        Expected response: {"status":"healthy"}

    ═══════════════════════════════════════════════════════════════════════════
    📊 RESOURCES CREATED:

    - Lightsail Container: ${var.project_name} (${var.container_power})
    - Lightsail Database: ${var.project_name}-db (PostgreSQL 17)
    - Lightsail DNS Zone: ${var.domain_name}
    - Lightsail Certificate: ${var.project_name}-cert (auto-validated)
    - IAM User: ${var.project_name}-cicd (for GitHub Actions)
    - .env file: deployment/prod/.env (automatically generated)

    💰 ESTIMATED MONTHLY COST: ~$25-26
    (Secrets stored in Terraform state - ensure state file is protected)
    ═══════════════════════════════════════════════════════════════════════════

    💡 CONFIGURATION WORKFLOW:

    - ✏️  Edit dynamic values:  terraform.tfvars (database, domains, secrets)
    - ✏️  Edit static values:   .env.base (invitations, feature flags)
    - 🔄 Apply changes:         terraform apply (regenerates .env automatically)
    - 📋 Update GitHub:         Copy new .env to ENV_FILE secret
    - 🚀 Deploy:                git push origin main

    See deployment/prod/ARCHITECTURE.md for full details.
    ═══════════════════════════════════════════════════════════════════════════
  EOT
}

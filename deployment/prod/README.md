# Production Deployment

Deploy Science Talk to AWS Lightsail with automatic secret generation and single-command infrastructure provisioning.

**Cost**: ~$25-26/month | **Setup time**: ~10 minutes | **Secrets**: Auto-generated

## Quick Start

```bash
# 1. Configure
just prod env-setup
vim deployment/prod/terraform.tfvars  # Set your domain

# 2. Deploy infrastructure (auto-generates secrets & .env)
just prod tf-init
just prod tf-apply

# 3. Setup GitHub Secrets
cat deployment/prod/.env | pbcopy
# GitHub → Settings → Secrets → Actions
# Add 3 secrets: ENV_FILE (paste), AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# 4. Deploy app
git push origin main

# 5. Verify
just prod health
```

## How It Works

### Single Source of Truth: `terraform.tfvars`

You only edit **one file** for all configuration:

```hcl
domain_name = "yourdomain.com"  # Required
subdomain   = "talk"            # Optional (default: "talk")
project_name = "talk"           # Optional (default: "talk")
```

Terraform automatically:
- ✅ Generates database password (32 chars, PostgreSQL-safe)
- ✅ Generates JWT secret (64 chars, high entropy)
- ✅ Creates AWS infrastructure (database, container service, DNS)
- ✅ Writes `.env` file with all configuration

### Generated `.env` File

After `terraform apply`, Terraform creates `deployment/prod/.env`:

```bash
export DATABASE__URL="postgresql+asyncpg://..."   # With generated password
export AUTH__JWT_SECRET="..."                     # Generated, 64 chars
export API__BASE_URL="https://talk.yourdomain.com"
export API__FRONTEND_URL="https://yourdomain.com"
```

**Important**: Never edit `.env` manually - it's regenerated on every `terraform apply`.

### Configuration Flow

```
terraform.tfvars (you edit)
    ↓
terraform apply
    ↓
├─ Creates AWS infrastructure
├─ Generates secrets
└─ Writes .env file
    ↓
Copy .env to GitHub ENV_FILE secret
    ↓
git push → GitHub Actions deploys
```

## Architecture

- **Container**: AWS Lightsail Container Service (micro: 0.5 vCPU, 1GB RAM, $10/mo)
- **Database**: Lightsail PostgreSQL 17 (micro: 1 vCPU, 2GB RAM, 40GB SSD, $15/mo)
- **DNS**: Route 53 hosted zone ($0.50/mo)
- **SSL**: Automatic via Lightsail
- **Secrets**: Terraform random provider (free, stored in state)
- **CI/CD**: GitHub Actions

**Total**: ~$25-26/month

## Infrastructure

### What Terraform Creates

- `talk` - Lightsail container service
- `talk-db` - Lightsail PostgreSQL 17 database
- `talk-cert` - SSL certificate
- Route 53 hosted zone + DNS records
- `.env` file with all configuration

### DNS Setup

After `terraform apply`, update nameservers at your domain registrar:

```bash
just prod tf-nameservers
```

Copy the nameservers and configure them at your registrar. DNS propagation takes 24-48 hours.

## Commands Reference

### Environment

```bash
just prod env-setup         # Create terraform.tfvars from template
just prod env-show          # Show current configuration
just prod env-show-secrets  # Show GitHub setup instructions
```

### Terraform

```bash
just prod tf-init           # Initialize Terraform
just prod tf-plan           # Preview changes
just prod tf-apply          # Deploy (also generates .env)
just prod tf-output         # Show all outputs
just prod tf-nameservers    # Get DNS nameservers
```

### Monitoring

```bash
just prod status            # Container service status
just prod logs              # Recent container logs
just prod health            # Test health endpoint
just prod info              # All status info
just prod db-status         # Database status
just prod db-snapshots      # List backups
```

### Deployment

```bash
just prod deploy            # Trigger GitHub Actions manually
just prod deploy-history    # Recent deployments
just prod checklist         # Full deployment checklist
```

## Updating Configuration

```bash
# 1. Edit configuration
vim deployment/prod/terraform.tfvars

# 2. Apply (regenerates .env)
just prod tf-apply

# 3. Update GitHub secret
cat deployment/prod/.env | pbcopy
# Update ENV_FILE secret in GitHub

# 4. Redeploy
git push origin main
```

## GitHub Secrets Setup

After `terraform apply`, add **3 secrets** to GitHub:

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `ENV_FILE` | Entire `.env` file | `cat deployment/prod/.env \| pbcopy` |
| `AWS_ACCESS_KEY_ID` | AWS access key | From AWS IAM Console |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | From AWS IAM Console |

**Location**: GitHub → Settings → Secrets and variables → Actions → New repository secret

## Security

### Files to Protect

| File | Contains | Protected By |
|------|----------|--------------|
| `terraform.tfvars` | Your domain config | `.gitignore` |
| `.env` | All secrets | `.gitignore`, file permissions 0600 |
| `terraform.tfstate` | Infrastructure state + secrets | `.gitignore` |

**Never commit** these files to git!

### Secret Storage

- **Terraform state**: Contains all secrets in plaintext (most sensitive file)
- **GitHub ENV_FILE**: Encrypted by GitHub, only accessible to Actions
- **Container environment**: Variables passed securely at deployment

### For Teams

Consider S3 backend for Terraform state:

```hcl
terraform {
  backend "s3" {
    bucket = "your-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
  }
}
```

## Scaling

### Container

```hcl
# In terraform.tfvars
container_power = "small"  # Options: micro ($10), small ($20), medium ($40)
container_scale = 2        # Number of instances
```

### Database

```hcl
# In terraform.tfvars
db_bundle_id = "small_2_0"  # Options: micro_2_0 ($15), small_2_0 ($30), medium_2_0 ($60)
```

Apply changes: `just prod tf-apply`

## Troubleshooting

### Container won't start
```bash
just prod logs              # Check container logs
just prod status            # Check deployment state
```

### Health check fails
```bash
just prod health            # Test endpoint
curl https://talk.yourdomain.com/health
```

### DNS not resolving
```bash
just prod tf-nameservers    # Verify nameservers
dig talk.yourdomain.com     # Check DNS propagation
```

### Database connection fails
```bash
just prod db-status         # Check database state
# Verify DATABASE__URL in .env matches Terraform output
```

### Secrets changed unexpectedly
Terraform preserves secrets with `lifecycle { ignore_changes = all }`. To rotate:
```bash
terraform taint random_password.db_password  # Or jwt_secret
terraform apply
# Update GitHub ENV_FILE secret
```

### Lost terraform.tfstate
**Critical**: State file contains secrets. If lost:
1. Recover secrets from `.env` if you have it
2. Otherwise, recreate infrastructure (data loss)
3. **Prevention**: Use S3 backend for state

## Cost Breakdown

| Service | Specs | Monthly Cost |
|---------|-------|--------------|
| Lightsail Container | 0.5 vCPU, 1GB RAM | $10 |
| Lightsail PostgreSQL | 1 vCPU, 2GB RAM, 40GB SSD | $15 |
| Route 53 | Hosted zone + queries | $0.50 |
| Data Transfer | Low traffic | ~$0.10 |
| **Total** | | **~$25-26** |

## Disaster Recovery

### Automatic Backups

- Database backups: Daily, 7-day retention
- Backup window: 03:00-04:00 UTC
- Final snapshot on deletion: Automatic

### Manual Backup

```bash
just prod db-snapshot       # Create manual snapshot
just prod db-snapshots      # List all snapshots
```

### Restore from Backup

Use AWS Console or CLI to restore from snapshot to new database instance.

## Vercel Frontend Integration

To point your Vercel apps to Route 53 DNS:

```hcl
# In terraform.tfvars
vercel_main_a_record = "76.76.21.21"         # Main app A record (from Vercel)
vercel_talk_cname    = "cname.vercel-dns.com" # Talk frontend CNAME (from Vercel)
```

This creates DNS records for:
- `amacrin.com` → Main Vercel app (A record)
- `talk.amacrin.com` → Talk frontend Vercel app (CNAME)
- `api.talk.amacrin.com` → API backend (CNAME to Lightsail - automatic)

## Deployment Readiness

### ✅ Critical (Completed - Ready to Deploy)

- [x] Database migrations in container startup (runs on every deploy)
- [x] CORS middleware configuration (allows talk.amacrin.com + localhost)
- [x] DNS configuration (api.talk.amacrin.com, talk.amacrin.com, amacrin.com)
- [x] Automatic secret generation (database password, JWT secret)
- [x] Health checks (/health endpoint)

### 🔵 Nice to Have (Post-Launch)

- [ ] OAuth security improvements (SSRF protection, DID verification)
- [ ] Rate limiting middleware
- [ ] Structured logging and monitoring
- [ ] CloudWatch alarms for errors/downtime
- [ ] Error handlers for better API responses

## Support

- View logs: `just prod logs`
- Health check: `just prod health`
- Full status: `just prod info`
- Deployment checklist: `just prod checklist`

For detailed command reference: `just prod`

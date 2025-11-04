# Science Talk - Terraform Variables

variable "project_name" {
  description = "Project name for resource naming (e.g., 'talk' for Science Talk)"
  type        = string
  default     = "talk"
}

variable "project_display_name" {
  description = "Human-readable project name"
  type        = string
  default     = "Science Talk"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile to use (optional, uses default if not set)"
  type        = string
  default     = null
}

variable "domain_name" {
  description = "Root domain name (e.g., yourdomain.com)"
  type        = string
}

variable "subdomain" {
  description = "Subdomain for the application"
  type        = string
  default     = "talk-api"
}

variable "frontend_subdomain" {
  description = "Subdomain for the API application"
  type        = string
  default     = "talk"
}

variable "db_bundle_id" {
  description = "Lightsail database bundle ID (micro_2_0 = 1 vCPU, 2GB RAM, $15/month)"
  type        = string
  default     = "micro_2_0"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "talk"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "dbadmin"
}

# Note: db_password is generated automatically by Terraform random provider
# See secrets.tf for implementation

variable "container_power" {
  description = "Lightsail container power (micro = 0.5 vCPU, 1GB RAM, $10/month)"
  type        = string
  default     = "micro"
}

variable "container_scale" {
  description = "Number of container instances"
  type        = number
  default     = 1
}

variable "vercel_main_a_record" {
  description = "Vercel A record IP for main app (amacrin.com)"
  type        = string
  default     = ""
}

variable "vercel_talk_cname" {
  description = "Vercel CNAME for talk frontend (talk.amacrin.com)"
  type        = string
  default     = ""
}

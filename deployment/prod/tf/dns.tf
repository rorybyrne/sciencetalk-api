# Science Talk - Lightsail DNS Configuration

# Lightsail DNS Zone
resource "aws_lightsail_domain" "main" {
  domain_name = var.domain_name
}

# CNAME record for API subdomain pointing to Lightsail container
resource "aws_lightsail_domain_entry" "api" {
  domain_name = aws_lightsail_domain.main.domain_name
  name        = var.subdomain
  type        = "CNAME"
  target      = trimprefix(trimsuffix(aws_lightsail_container_service.main.url, "/"), "https://")
}

# Vercel DNS records

# Main Vercel app at root domain (apex)
resource "aws_lightsail_domain_entry" "vercel_main" {
  count       = var.vercel_main_a_record != "" ? 1 : 0
  domain_name = aws_lightsail_domain.main.domain_name
  name        = ""  # Empty string for apex/root domain
  type        = "A"
  target      = var.vercel_main_a_record
}

# Talk Vercel app at talk subdomain
# resource "aws_lightsail_domain_entry" "vercel_talk" {
#   provider    = aws.us_east_1
#   count       = var.vercel_talk_cname != "" ? 1 : 0
#   domain_name = aws_lightsail_domain.main.domain_name
#   name        = "talk"
#   type        = "CNAME"
#   target      = var.vercel_talk_cname
#
#   lifecycle {
#     ignore_changes = all
#   }
# }

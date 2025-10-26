# Science Talk - Route 53 DNS Configuration

# Route 53 Hosted Zone
resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = {
    Name    = "${var.project_name}-zone"
    Project = var.project_display_name
  }
}

# CNAME for application subdomain pointing to Lightsail container
resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "${var.subdomain}.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300

  # Extract hostname from Lightsail URL (remove https:// prefix)
  records = [
    replace(aws_lightsail_container_service.main.url, "https://", "")
  ]
}

# Optional: Vercel DNS records (if using Vercel for frontends)

# Main Vercel app at root domain (amacrin.com)
resource "aws_route53_record" "vercel_main" {
  count   = var.vercel_main_a_record != "" ? 1 : 0
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [var.vercel_main_a_record]
}

# Talk Vercel app at talk subdomain (talk.amacrin.com)
resource "aws_route53_record" "vercel_talk" {
  count   = var.vercel_talk_cname != "" ? 1 : 0
  zone_id = aws_route53_zone.main.zone_id
  name    = "talk.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = [var.vercel_talk_cname]
}

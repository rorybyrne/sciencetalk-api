# Science Talk - CI/CD IAM User
#
# Creates a dedicated IAM user for GitHub Actions with minimal required permissions.

# Create IAM user for CI/CD
resource "aws_iam_user" "cicd" {
  name = "${var.project_name}-cicd"
  path = "/cicd/"

  tags = {
    Name        = "${var.project_name}-cicd"
    Environment = "production"
    ManagedBy   = "terraform"
    Purpose     = "GitHub Actions deployment"
  }
}

# Create access key for the CI/CD user
resource "aws_iam_access_key" "cicd" {
  user = aws_iam_user.cicd.name
}

# Create IAM policy with minimal permissions for Lightsail deployment
resource "aws_iam_policy" "cicd_lightsail" {
  name        = "${var.project_name}-cicd-lightsail"
  description = "Minimal permissions for CI/CD to deploy to Lightsail"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LightsailContainerImageManagement"
        Effect = "Allow"
        Action = [
          "lightsail:PushContainerImage",
          "lightsail:RegisterContainerImage",
          "lightsail:CreateContainerServiceRegistryLogin",
          "lightsail:GetContainerServices",
          "lightsail:GetContainerServiceDeployments",
        ]
        Resource = "*"
      },
      {
        Sid    = "LightsailContainerServiceManagement"
        Effect = "Allow"
        Action = [
          "lightsail:CreateContainerServiceDeployment",
          "lightsail:UpdateContainerService",
        ]
        Resource = aws_lightsail_container_service.main.arn
      },
    ]
  })
}

# Attach policy to CI/CD user
resource "aws_iam_user_policy_attachment" "cicd_lightsail" {
  user       = aws_iam_user.cicd.name
  policy_arn = aws_iam_policy.cicd_lightsail.arn
}

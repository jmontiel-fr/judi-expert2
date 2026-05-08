# ==============================================
# VPC + Lightsail VPC Peering
# Uses the default VPC (required for Lightsail peering)
# and enables peering via null_resource
# ==============================================

# --- Use default VPC (Lightsail can only peer with default VPC) ---
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# --- Enable Lightsail VPC Peering (idempotent) ---
resource "null_resource" "lightsail_vpc_peering" {
  provisioner "local-exec" {
    command = "aws lightsail peer-vpc --region ${var.aws_region}"
  }

  # Re-run if region changes
  triggers = {
    region = var.aws_region
  }
}

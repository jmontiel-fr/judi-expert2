# ==============================================
# Lightsail — Instance Docker (CloudFront handles HTTPS)
# ==============================================

resource "aws_lightsail_instance" "main" {
  name              = "${var.project_name}-${var.environment}"
  availability_zone = "${var.aws_region}a"
  blueprint_id      = "amazon_linux_2023"
  bundle_id         = var.instance_plan

  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Install Docker
    yum update -y
    yum install -y docker git
    systemctl enable docker
    systemctl start docker

    # Install Docker Compose plugin
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

    # Create app directory
    mkdir -p /opt/judi-expert
    echo "Instance ready for deployment" > /opt/judi-expert/status.txt
  EOF

  tags = {
    Name        = "${var.project_name}-${var.environment}"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Static IP
resource "aws_lightsail_static_ip" "main" {
  name = "${var.project_name}-${var.environment}-ip"
}

resource "aws_lightsail_static_ip_attachment" "main" {
  static_ip_name = aws_lightsail_static_ip.main.name
  instance_name  = aws_lightsail_instance.main.name
}

# Open ports: 3000 (frontend) + 8000 (backend) for CloudFront + SSH (22)
resource "aws_lightsail_instance_public_ports" "main" {
  instance_name = aws_lightsail_instance.main.name

  port_info {
    protocol  = "tcp"
    from_port = 3000
    to_port   = 3000
  }

  port_info {
    protocol  = "tcp"
    from_port = 8000
    to_port   = 8000
  }

  port_info {
    protocol  = "tcp"
    from_port = 22
    to_port   = 22
  }
}

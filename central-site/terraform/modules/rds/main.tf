# ==============================================
# RDS PostgreSQL — Judi-Expert Site Central
# Private, in default VPC, accessible via Lightsail VPC Peering
# ==============================================

# --- Security Group for RDS ---
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Allow PostgreSQL access from Lightsail VPC (peered)"
  vpc_id      = var.vpc_id

  ingress {
    description = "PostgreSQL from Lightsail VPC (peered CIDR 172.26.0.0/16)"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["172.26.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-sg"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- DB Subnet Group (default VPC subnets) ---
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- RDS Instance ---
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}-db"

  engine         = "postgres"
  engine_version = "15"
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  multi_az            = false
  publicly_accessible = false

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  skip_final_snapshot       = true
  final_snapshot_identifier = "${var.project_name}-${var.environment}-final"

  deletion_protection = false

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

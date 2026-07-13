# ==============================================
# Module S3 — Bucket pour les packages Site Client
# Stocke les installateurs (.exe, .sh) et les images Docker (.tar.gz)
# Accès : privé, presigned URLs générées par le backend
# ==============================================

resource "aws_s3_bucket" "assets" {
  bucket = "judi-expert-assets-eu-west-3"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "Client packages and Docker images"
  }
}

# Bloquer tout accès public
resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Chiffrement côté serveur (AES256)
resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versionning désactivé (les installateurs sont immuables par version)
resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id

  versioning_configuration {
    status = "Disabled"
  }
}

# Lifecycle : supprimer les anciennes versions après 90 jours
resource "aws_s3_bucket_lifecycle_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    id     = "cleanup-old-packages"
    status = "Enabled"

    filter {
      prefix = "packages/"
    }

    expiration {
      days = 365
    }
  }
}

# IAM Policy pour que le backend (Lightsail) puisse générer des presigned URLs
resource "aws_iam_user" "backend_s3" {
  name = "${var.project_name}-${var.environment}-backend-s3"

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_iam_user_policy" "backend_s3_access" {
  name = "${var.project_name}-s3-read-packages"
  user = aws_iam_user.backend_s3.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.assets.arn,
          "${aws_s3_bucket.assets.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_access_key" "backend_s3" {
  user = aws_iam_user.backend_s3.name
}

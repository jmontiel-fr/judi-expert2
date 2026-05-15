# ==============================================
# Judi-Expert — Module Cron Abonnement
# EventBridge → Lambda → POST /api/internal/cron/subscription-check
# ==============================================

# --- Secrets Manager : Token d'authentification du cron ---

resource "aws_secretsmanager_secret" "cron_token" {
  name        = "${var.project_name}-${var.environment}-cron-token"
  description = "Token d'authentification pour l'endpoint interne du cron abonnement"

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "cron_token" {
  secret_id = aws_secretsmanager_secret.cron_token.id
  secret_string = jsonencode({
    token = random_password.cron_token.result
  })
}

resource "random_password" "cron_token" {
  length  = 64
  special = false
}

# --- IAM Role pour la Lambda ---

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cron_lambda_role" {
  name               = "${var.project_name}-${var.environment}-cron-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Permissions minimales : CloudWatch Logs + Secrets Manager (lecture du token)
data "aws_iam_policy_document" "cron_lambda_policy" {
  # CloudWatch Logs
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-${var.environment}-cron-abonnement:*"]
  }

  # Secrets Manager — lecture du token cron uniquement
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [aws_secretsmanager_secret.cron_token.arn]
  }
}

resource "aws_iam_role_policy" "cron_lambda_policy" {
  name   = "${var.project_name}-${var.environment}-cron-lambda-policy"
  role   = aws_iam_role.cron_lambda_role.id
  policy = data.aws_iam_policy_document.cron_lambda_policy.json
}

# --- Lambda Function ---

data "archive_file" "cron_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_src"
  output_path = "${path.module}/lambda_cron_abonnement.zip"
}

resource "aws_lambda_function" "cron_abonnement" {
  function_name = "${var.project_name}-${var.environment}-cron-abonnement"
  description   = "Cron quotidien - vérification des incidents de paiement d'abonnement"

  filename         = data.archive_file.cron_lambda_zip.output_path
  source_code_hash = data.archive_file.cron_lambda_zip.output_base64sha256
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = var.lambda_timeout

  role = aws_iam_role.cron_lambda_role.arn

  environment {
    variables = {
      API_BASE_URL   = var.api_base_url
      SECRET_NAME    = aws_secretsmanager_secret.cron_token.name
      AWS_REGION_NAME = var.aws_region
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# --- CloudWatch Log Group (rétention 14 jours) ---

resource "aws_cloudwatch_log_group" "cron_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.cron_abonnement.function_name}"
  retention_in_days = 14

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# --- EventBridge Rule (cron quotidien) ---

resource "aws_cloudwatch_event_rule" "cron_abonnement" {
  name                = "${var.project_name}-${var.environment}-cron-abonnement"
  description         = "Déclenchement quotidien à 08:00 UTC pour la vérification des abonnements"
  schedule_expression = var.schedule_expression

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# --- EventBridge Target → Lambda ---

resource "aws_cloudwatch_event_target" "cron_lambda" {
  rule      = aws_cloudwatch_event_rule.cron_abonnement.name
  target_id = "cron-abonnement-lambda"
  arn       = aws_lambda_function.cron_abonnement.arn
}

# --- Permission pour EventBridge d'invoquer la Lambda ---

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cron_abonnement.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cron_abonnement.arn
}

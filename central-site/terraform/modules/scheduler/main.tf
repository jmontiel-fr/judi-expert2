# ==============================================
# Scheduler Heures Ouvrables — Judi-Expert Site Central
# ==============================================
# Démarrage automatique à 8h et arrêt à 20h (Europe/Paris)
# du lundi au vendredi via EventBridge Scheduler + Lambda.
# ==============================================

locals {
  prefix = "${var.project_name}-${var.environment}"
}

# --- Data: Package Lambda source files ---

data "archive_file" "site_start" {
  type        = "zip"
  source_file = "${path.module}/lambda/site_start.py"
  output_path = "${path.module}/lambda/.dist/site_start.zip"
}

data "archive_file" "site_stop" {
  type        = "zip"
  source_file = "${path.module}/lambda/site_stop.py"
  output_path = "${path.module}/lambda/.dist/site_stop.zip"
}

# ==============================================
# IAM — Lambda Execution Role
# ==============================================

resource "aws_iam_role" "scheduler_lambda" {
  name = "${local.prefix}-scheduler-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.prefix}-scheduler-lambda"
  }
}

resource "aws_iam_role_policy" "scheduler_lambda" {
  name = "${local.prefix}-scheduler-lambda-policy"
  role = aws_iam_role.scheduler_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "rds:StartDBInstance",
          "rds:StopDBInstance",
          "rds:DescribeDBInstances"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# ==============================================
# CloudWatch Log Groups
# ==============================================

resource "aws_cloudwatch_log_group" "site_start" {
  name              = "/aws/lambda/${local.prefix}-site-start"
  retention_in_days = 30

  tags = {
    Name = "${local.prefix}-site-start-logs"
  }
}

resource "aws_cloudwatch_log_group" "site_stop" {
  name              = "/aws/lambda/${local.prefix}-site-stop"
  retention_in_days = 30

  tags = {
    Name = "${local.prefix}-site-stop-logs"
  }
}

# ==============================================
# Lambda Functions
# ==============================================

resource "aws_lambda_function" "site_start" {
  function_name    = "${local.prefix}-site-start"
  role             = aws_iam_role.scheduler_lambda.arn
  handler          = "site_start.handler"
  runtime          = "python3.12"
  timeout          = 300
  filename         = data.archive_file.site_start.output_path
  source_code_hash = data.archive_file.site_start.output_base64sha256

  environment {
    variables = {
      ECS_CLUSTER     = var.ecs_cluster_name
      ECS_SERVICE     = var.ecs_service_name
      RDS_INSTANCE_ID = var.rds_instance_id
    }
  }

  depends_on = [aws_cloudwatch_log_group.site_start]

  tags = {
    Name = "${local.prefix}-site-start"
  }
}

resource "aws_lambda_function" "site_stop" {
  function_name    = "${local.prefix}-site-stop"
  role             = aws_iam_role.scheduler_lambda.arn
  handler          = "site_stop.handler"
  runtime          = "python3.12"
  timeout          = 60
  filename         = data.archive_file.site_stop.output_path
  source_code_hash = data.archive_file.site_stop.output_base64sha256

  environment {
    variables = {
      ECS_CLUSTER     = var.ecs_cluster_name
      ECS_SERVICE     = var.ecs_service_name
      RDS_INSTANCE_ID = var.rds_instance_id
    }
  }

  depends_on = [aws_cloudwatch_log_group.site_stop]

  tags = {
    Name = "${local.prefix}-site-stop"
  }
}

# ==============================================
# IAM — EventBridge Scheduler Execution Role
# ==============================================

resource "aws_iam_role" "scheduler_eventbridge" {
  name = "${local.prefix}-scheduler-eventbridge"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.prefix}-scheduler-eventbridge"
  }
}

resource "aws_iam_role_policy" "scheduler_eventbridge" {
  name = "${local.prefix}-scheduler-eventbridge-policy"
  role = aws_iam_role.scheduler_eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.site_start.arn,
          aws_lambda_function.site_stop.arn
        ]
      }
    ]
  })
}

# ==============================================
# EventBridge Scheduler — Schedules (timezone-aware)
# ==============================================

resource "aws_scheduler_schedule" "site_start" {
  name       = "${local.prefix}-site-start"
  group_name = "default"

  schedule_expression          = "cron(0 8 ? * MON-FRI *)"
  schedule_expression_timezone = "Europe/Paris"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.site_start.arn
    role_arn = aws_iam_role.scheduler_eventbridge.arn
  }
}

resource "aws_scheduler_schedule" "site_stop" {
  name       = "${local.prefix}-site-stop"
  group_name = "default"

  schedule_expression          = "cron(0 20 ? * MON-FRI *)"
  schedule_expression_timezone = "Europe/Paris"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.site_stop.arn
    role_arn = aws_iam_role.scheduler_eventbridge.arn
  }
}

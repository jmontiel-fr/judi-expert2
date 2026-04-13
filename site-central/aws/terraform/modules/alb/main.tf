# ==============================================
# ALB — Judi-Expert Site Central
# ==============================================

# --- Application Load Balancer ---

resource "aws_lb" "main" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-alb"
  }
}

# --- Target Group — Backend (port 8000) ---

resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-${var.environment}-backend"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-backend-tg"
  }
}

# --- Target Group — Frontend (port 3000) ---

resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-${var.environment}-frontend"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-frontend-tg"
  }
}

# --- HTTP Listener (port 80) ---
# Default action: fixed-response 503 (maintenance mode)
# Forward rules have higher priority and are active during normal operation.
# The scheduler (task 17.4) toggles between maintenance and normal mode.

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/html"
      message_body = <<-HTML
        <!DOCTYPE html>
        <html lang="fr">
        <head><meta charset="UTF-8"><title>Judi-Expert — Maintenance</title>
        <style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f5f5f5;color:#333}
        .container{text-align:center;padding:2rem}h1{color:#1a237e}p{font-size:1.2rem}</style></head>
        <body><div class="container">
        <h1>Judi-Expert</h1>
        <p>Site en maintenance &mdash; Horaires : 8h-20h (heure de Paris)</p>
        <p><a href="mailto:contact@judi-expert.fr">Contactez-nous</a></p>
        </div></body></html>
      HTML
      status_code  = "503"
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-http-listener"
  }
}

# --- Listener Rule — Backend (/api/*) — Priority 100 ---

resource "aws_lb_listener_rule" "backend" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-backend-rule"
  }
}

# --- Listener Rule — Frontend (all other paths) — Priority 200 ---

resource "aws_lb_listener_rule" "frontend" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-frontend-rule"
  }
}

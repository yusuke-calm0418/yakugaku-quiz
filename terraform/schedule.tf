resource "aws_iam_role" "schedule" {
  name = "${var.project_name}-schedule"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_cloudwatch_log_group" "schedule" {
  name              = "/aws/lambda/${var.project_name}-schedule"
  retention_in_days = 7
}

resource "aws_iam_role_policy" "schedule" {
  role = aws_iam_role.schedule.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "ec2:DescribeInstances", Resource = "*" },
      { Effect = "Allow", Action = ["ec2:StartInstances", "ec2:StopInstances"], Resource = aws_instance.web.arn },
      { Effect = "Allow", Action = ["rds:DescribeDBInstances", "rds:StartDBInstance", "rds:StopDBInstance"], Resource = aws_db_instance.postgres.arn },
      { Effect = "Allow", Action = "route53:ListResourceRecordSets", Resource = "arn:aws:route53:::hostedzone/${var.hosted_zone_id}" },
      {
        Effect = "Allow", Action = "route53:ChangeResourceRecordSets", Resource = "arn:aws:route53:::hostedzone/${var.hosted_zone_id}"
        Condition = { "ForAllValues:StringEquals" = {
          "route53:ChangeResourceRecordSetsNormalizedRecordNames" = [lower(local.origin_domain)]
          "route53:ChangeResourceRecordSetsRecordTypes"           = ["A"]
          "route53:ChangeResourceRecordSetsActions"               = ["UPSERT"]
        } }
      },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.schedule.arn}:*" }
    ]
  })
}

data "archive_file" "schedule" {
  type        = "zip"
  source_file = "${path.module}/lambda/schedule.py"
  output_path = "${path.module}/.terraform/schedule.zip"
}

resource "aws_lambda_function" "schedule" {
  function_name                  = "${var.project_name}-schedule"
  role                           = aws_iam_role.schedule.arn
  runtime                        = "python3.12"
  architectures                  = ["arm64"]
  handler                        = "schedule.handler"
  filename                       = data.archive_file.schedule.output_path
  source_code_hash               = data.archive_file.schedule.output_base64sha256
  timeout                        = 60
  memory_size                    = 128
  reserved_concurrent_executions = 1
  environment {
    variables = {
      INSTANCE_ID           = aws_instance.web.id
      DB_ID                 = aws_db_instance.postgres.identifier
      ZONE_ID               = var.hosted_zone_id
      ORIGIN_DOMAIN         = local.origin_domain
      HOLIDAY_DATES         = jsonencode(sort(tolist(var.holiday_dates)))
      HOLIDAY_CALENDAR_YEAR = tostring(var.holiday_calendar_year)
    }
  }
  depends_on = [aws_iam_role_policy.schedule]
}

resource "aws_iam_role" "scheduler" {
  name = "${var.project_name}-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Principal = { Service = "scheduler.amazonaws.com" }, Action = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "lambda:InvokeFunction", Resource = aws_lambda_function.schedule.arn }]
  })
}

resource "aws_scheduler_schedule" "operate" {
  name                         = "${var.project_name}-operate"
  schedule_expression          = "cron(0/5 * * * ? *)"
  schedule_expression_timezone = "Asia/Tokyo"
  flexible_time_window {
    mode = "OFF"
  }
  target {
    arn      = aws_lambda_function.schedule.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = "{}"
    retry_policy {
      maximum_event_age_in_seconds = 300
      maximum_retry_attempts       = 2
    }
  }
  depends_on = [aws_iam_role_policy.scheduler]
}

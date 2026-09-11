resource "aws_budgets_budget" "monthly" {
  name         = "${var.project_name}-monthly"
  budget_type  = "COST"
  limit_amount = format("%.2f", 3000 / var.budget_usd_jpy)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = toset(["1500", "2000", "2500"])
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = tonumber(notification.value) / var.budget_usd_jpy
      threshold_type             = "ABSOLUTE_VALUE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.budget_email]
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "health" {
  for_each = {
    ec2      = { namespace = "AWS/EC2", metric = "StatusCheckFailed", dimensions = { InstanceId = aws_instance.web.id } }
    schedule = { namespace = "AWS/Lambda", metric = "Errors", dimensions = { FunctionName = aws_lambda_function.schedule.function_name } }
  }
  alarm_name          = "${var.project_name}-${each.key}-errors"
  namespace           = each.value.namespace
  metric_name         = each.value.metric
  dimensions          = each.value.dimensions
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "db_storage" {
  alarm_name          = "${var.project_name}-db-low-storage"
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.postgres.identifier }
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "LessThanThreshold"
  threshold           = 2147483648
  treat_missing_data  = "notBreaching"
}

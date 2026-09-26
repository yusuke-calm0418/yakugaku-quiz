locals {
  origin_domain   = "origin.${var.domain_name}"
  route53_zone_id = var.use_ministack ? aws_route53_zone.local[0].zone_id : var.hosted_zone_id
}

resource "aws_route53_zone" "local" {
  count = var.use_ministack ? 1 : 0

  name = var.domain_name
}

# ==========================================
# ACM Certificate
# ==========================================


resource "aws_acm_certificate" "site" {
  provider = aws.us_east_1

  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "certificate" {
  for_each = {
    for option in aws_acm_certificate.site.domain_validation_options :
    option.domain_name => option
  }

  zone_id = local.route53_zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  records = [each.value.resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "site" {
  provider = aws.us_east_1

  certificate_arn = aws_acm_certificate.site.arn

  validation_record_fqdns = [
    for record in aws_route53_record.certificate :
    record.fqdn
  ]
}

# ==========================================
# EC2 Origin DNS
# ==========================================

resource "aws_route53_record" "origin" {
  zone_id = local.route53_zone_id
  name    = local.origin_domain
  type    = "A"
  ttl     = 60

  records = [
    aws_instance.web.public_ip
  ]

  lifecycle {
    # 起動後のIP更新はLambdaが担当
    ignore_changes = [records]
  }
}

# ==========================================
# CloudFront Origin Access Control
# ==========================================

resource "aws_cloudfront_origin_access_control" "assets" {
  provider = aws.us_east_1

  name                              = "${var.project_name}-assets"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ==========================================
# CloudFront Cache Policies
#
# MiniStackにはAWS管理ポリシー
# Managed-CachingDisabled /
# Managed-CachingOptimized が存在しないため
# Terraformで作成する
# ==========================================

resource "aws_cloudfront_cache_policy" "disabled" {
  provider = aws.us_east_1

  name        = "${var.project_name}-caching-disabled"
  comment     = "Disable caching for Django dynamic contents"
  min_ttl     = 0
  default_ttl = 0
  max_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = false
    enable_accept_encoding_gzip   = false

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_cloudfront_cache_policy" "optimized" {
  provider = aws.us_east_1

  name        = "${var.project_name}-caching-optimized"
  comment     = "Cache static and media assets"
  min_ttl     = 1
  default_ttl = 86400
  max_ttl     = 31536000

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

# ==========================================
# CloudFront Origin Request Policy
#
# AWS Managed-AllViewer の代わりに
# Terraformで作成する
# ==========================================

resource "aws_cloudfront_origin_request_policy" "all_viewer" {
  provider = aws.us_east_1

  name    = "${var.project_name}-all-viewer"
  comment = "Forward viewer request data to Django origin"

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "allViewer"
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

# ==========================================
# CloudFront Distribution
# ==========================================

resource "aws_cloudfront_distribution" "site" {
  provider = aws.us_east_1

  enabled         = true
  is_ipv6_enabled = true
  aliases         = [var.domain_name]
  price_class     = "PriceClass_200"

  # ----------------------------------------
  # Django / EC2 Origin
  # ----------------------------------------

  origin {
    domain_name = aws_route53_record.origin.fqdn
    origin_id   = "ec2"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"

      origin_ssl_protocols = [
        "TLSv1.2"
      ]
    }
  }

  # ----------------------------------------
  # Static / Media S3 Origin
  # ----------------------------------------

  origin {
    domain_name = aws_s3_bucket.assets.bucket_regional_domain_name
    origin_id   = "s3"

    origin_access_control_id = aws_cloudfront_origin_access_control.assets.id
  }

  # ----------------------------------------
  # Django Dynamic Contents
  # ----------------------------------------

  default_cache_behavior {
    target_origin_id       = "ec2"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = [
      "GET",
      "HEAD",
      "OPTIONS",
      "PUT",
      "POST",
      "PATCH",
      "DELETE"
    ]

    cached_methods = [
      "GET",
      "HEAD"
    ]

    cache_policy_id = aws_cloudfront_cache_policy.disabled.id

    origin_request_policy_id = aws_cloudfront_origin_request_policy.all_viewer.id

    compress = true
  }

  # ----------------------------------------
  # Static / Media
  # ----------------------------------------

  dynamic "ordered_cache_behavior" {
    for_each = [
      "/static/*",
      "/media/*"
    ]

    content {
      path_pattern     = ordered_cache_behavior.value
      target_origin_id = "s3"

      viewer_protocol_policy = "redirect-to-https"

      allowed_methods = [
        "GET",
        "HEAD",
        "OPTIONS"
      ]

      cached_methods = [
        "GET",
        "HEAD"
      ]

      cache_policy_id = aws_cloudfront_cache_policy.optimized.id

      compress = true
    }
  }

  # ----------------------------------------
  # Restrictions
  # ----------------------------------------

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # ----------------------------------------
  # TLS
  # ----------------------------------------

  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate_validation.site.certificate_arn

    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

# ==========================================
# Route53
# ==========================================

resource "aws_route53_record" "site" {
  for_each = toset([
    "A",
    "AAAA"
  ])

  zone_id = local.route53_zone_id
  name    = var.domain_name
  type    = each.value

  alias {
    name = aws_cloudfront_distribution.site.domain_name

    zone_id = aws_cloudfront_distribution.site.hosted_zone_id

    evaluate_target_health = false
  }
}

# ==========================================
# S3 Bucket Policy
# ==========================================

resource "aws_s3_bucket_policy" "assets" {
  bucket = aws_s3_bucket.assets.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "cloudfront.amazonaws.com"
        }

        Action = "s3:GetObject"

        Resource = [
          "${aws_s3_bucket.assets.arn}/static/*",
          "${aws_s3_bucket.assets.arn}/media/*"
        ]

        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.site.arn
          }
        }
      }
    ]
  })
}
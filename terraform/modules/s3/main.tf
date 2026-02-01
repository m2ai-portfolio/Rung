# Rung S3 Module - HIPAA Compliant Storage Buckets
# Creates encrypted S3 buckets for voice memos, transcripts, and exports

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    HIPAA       = "true"
  })
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

#------------------------------------------------------------------------------
# Voice Memos Bucket
#------------------------------------------------------------------------------
resource "aws_s3_bucket" "voice_memos" {
  bucket = "${local.name_prefix}-voice-memos"

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-voice-memos"
    Purpose = "voice-memo-uploads"
  })
}

resource "aws_s3_bucket_versioning" "voice_memos" {
  bucket = aws_s3_bucket.voice_memos.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "voice_memos" {
  bucket = aws_s3_bucket.voice_memos.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.s3_kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "voice_memos" {
  bucket = aws_s3_bucket.voice_memos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "voice_memos" {
  bucket = aws_s3_bucket.voice_memos.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER"
    }

    noncurrent_version_transition {
      noncurrent_days = var.glacier_transition_days
      storage_class   = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_logging" "voice_memos" {
  count = var.logging_bucket_id != null ? 1 : 0

  bucket = aws_s3_bucket.voice_memos.id

  target_bucket = var.logging_bucket_id
  target_prefix = "s3-access-logs/voice-memos/"
}

#------------------------------------------------------------------------------
# Transcripts Bucket
#------------------------------------------------------------------------------
resource "aws_s3_bucket" "transcripts" {
  bucket = "${local.name_prefix}-transcripts"

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-transcripts"
    Purpose = "transcription-output"
  })
}

resource "aws_s3_bucket_versioning" "transcripts" {
  bucket = aws_s3_bucket.transcripts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "transcripts" {
  bucket = aws_s3_bucket.transcripts.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.s3_kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "transcripts" {
  bucket = aws_s3_bucket.transcripts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "transcripts" {
  bucket = aws_s3_bucket.transcripts.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER"
    }

    noncurrent_version_transition {
      noncurrent_days = var.glacier_transition_days
      storage_class   = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_logging" "transcripts" {
  count = var.logging_bucket_id != null ? 1 : 0

  bucket = aws_s3_bucket.transcripts.id

  target_bucket = var.logging_bucket_id
  target_prefix = "s3-access-logs/transcripts/"
}

#------------------------------------------------------------------------------
# Exports Bucket
#------------------------------------------------------------------------------
resource "aws_s3_bucket" "exports" {
  bucket = "${local.name_prefix}-exports"

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-exports"
    Purpose = "data-export-requests"
  })
}

resource "aws_s3_bucket_versioning" "exports" {
  bucket = aws_s3_bucket.exports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.s3_kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "exports" {
  bucket = aws_s3_bucket.exports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER"
    }

    noncurrent_version_transition {
      noncurrent_days = var.glacier_transition_days
      storage_class   = "GLACIER"
    }
  }

  rule {
    id     = "expire-old-exports"
    status = "Enabled"

    expiration {
      days = var.exports_expiration_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.exports_expiration_days
    }
  }
}

resource "aws_s3_bucket_logging" "exports" {
  count = var.logging_bucket_id != null ? 1 : 0

  bucket = aws_s3_bucket.exports.id

  target_bucket = var.logging_bucket_id
  target_prefix = "s3-access-logs/exports/"
}

#------------------------------------------------------------------------------
# Bucket Policies - Restrict to VPC Endpoint and specific roles
#------------------------------------------------------------------------------
resource "aws_s3_bucket_policy" "voice_memos" {
  bucket = aws_s3_bucket.voice_memos.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyNonVPCAccess"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.voice_memos.arn,
          "${aws_s3_bucket.voice_memos.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "aws:SourceVpce" = var.vpc_endpoint_id
          }
          Bool = {
            "aws:ViaAWSService" = "false"
          }
        }
      },
      {
        Sid       = "EnforceHTTPS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.voice_memos.arn,
          "${aws_s3_bucket.voice_memos.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "transcripts" {
  bucket = aws_s3_bucket.transcripts.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowTranscribeService"
        Effect    = "Allow"
        Principal = {
          Service = "transcribe.amazonaws.com"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.transcripts.arn}/*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid       = "EnforceHTTPS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.transcripts.arn,
          "${aws_s3_bucket.transcripts.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "exports" {
  bucket = aws_s3_bucket.exports.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyNonVPCAccess"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.exports.arn,
          "${aws_s3_bucket.exports.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "aws:SourceVpce" = var.vpc_endpoint_id
          }
          Bool = {
            "aws:ViaAWSService" = "false"
          }
        }
      },
      {
        Sid       = "EnforceHTTPS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.exports.arn,
          "${aws_s3_bucket.exports.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

#------------------------------------------------------------------------------
# CORS Configuration (for voice memo upload)
#------------------------------------------------------------------------------
resource "aws_s3_bucket_cors_configuration" "voice_memos" {
  bucket = aws_s3_bucket.voice_memos.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

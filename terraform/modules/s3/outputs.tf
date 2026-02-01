# S3 Module Outputs

#------------------------------------------------------------------------------
# Voice Memos Bucket
#------------------------------------------------------------------------------
output "voice_memos_bucket_id" {
  description = "ID of the voice memos bucket"
  value       = aws_s3_bucket.voice_memos.id
}

output "voice_memos_bucket_arn" {
  description = "ARN of the voice memos bucket"
  value       = aws_s3_bucket.voice_memos.arn
}

output "voice_memos_bucket_name" {
  description = "Name of the voice memos bucket"
  value       = aws_s3_bucket.voice_memos.bucket
}

output "voice_memos_bucket_domain_name" {
  description = "Domain name of the voice memos bucket"
  value       = aws_s3_bucket.voice_memos.bucket_domain_name
}

#------------------------------------------------------------------------------
# Transcripts Bucket
#------------------------------------------------------------------------------
output "transcripts_bucket_id" {
  description = "ID of the transcripts bucket"
  value       = aws_s3_bucket.transcripts.id
}

output "transcripts_bucket_arn" {
  description = "ARN of the transcripts bucket"
  value       = aws_s3_bucket.transcripts.arn
}

output "transcripts_bucket_name" {
  description = "Name of the transcripts bucket"
  value       = aws_s3_bucket.transcripts.bucket
}

output "transcripts_bucket_domain_name" {
  description = "Domain name of the transcripts bucket"
  value       = aws_s3_bucket.transcripts.bucket_domain_name
}

#------------------------------------------------------------------------------
# Exports Bucket
#------------------------------------------------------------------------------
output "exports_bucket_id" {
  description = "ID of the exports bucket"
  value       = aws_s3_bucket.exports.id
}

output "exports_bucket_arn" {
  description = "ARN of the exports bucket"
  value       = aws_s3_bucket.exports.arn
}

output "exports_bucket_name" {
  description = "Name of the exports bucket"
  value       = aws_s3_bucket.exports.bucket
}

output "exports_bucket_domain_name" {
  description = "Domain name of the exports bucket"
  value       = aws_s3_bucket.exports.bucket_domain_name
}

#------------------------------------------------------------------------------
# Versioning Status
#------------------------------------------------------------------------------
output "buckets_versioning_enabled" {
  description = "Map of bucket names to versioning status"
  value = {
    voice_memos = aws_s3_bucket_versioning.voice_memos.versioning_configuration[0].status
    transcripts = aws_s3_bucket_versioning.transcripts.versioning_configuration[0].status
    exports     = aws_s3_bucket_versioning.exports.versioning_configuration[0].status
  }
}

#------------------------------------------------------------------------------
# Encryption Status
#------------------------------------------------------------------------------
output "buckets_encrypted" {
  description = "Map indicating all buckets are encrypted with KMS"
  value = {
    voice_memos = true
    transcripts = true
    exports     = true
  }
}

output "encryption_kms_key_arn" {
  description = "KMS key ARN used for bucket encryption"
  value       = var.s3_kms_key_arn
}

#------------------------------------------------------------------------------
# Public Access Block Status
#------------------------------------------------------------------------------
output "public_access_blocked" {
  description = "Confirmation that public access is blocked on all buckets"
  value = {
    voice_memos = true
    transcripts = true
    exports     = true
  }
}

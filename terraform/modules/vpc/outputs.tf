# VPC Module Outputs

#------------------------------------------------------------------------------
# VPC
#------------------------------------------------------------------------------
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "vpc_arn" {
  description = "ARN of the VPC"
  value       = aws_vpc.main.arn
}

#------------------------------------------------------------------------------
# Subnets
#------------------------------------------------------------------------------
output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "public_subnet_cidrs" {
  description = "List of public subnet CIDR blocks"
  value       = aws_subnet.public[*].cidr_block
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "private_subnet_cidrs" {
  description = "List of private subnet CIDR blocks"
  value       = aws_subnet.private[*].cidr_block
}

output "public_subnet_azs" {
  description = "List of availability zones for public subnets"
  value       = aws_subnet.public[*].availability_zone
}

output "private_subnet_azs" {
  description = "List of availability zones for private subnets"
  value       = aws_subnet.private[*].availability_zone
}

#------------------------------------------------------------------------------
# NAT Gateway
#------------------------------------------------------------------------------
output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.main[*].id
}

output "nat_gateway_public_ips" {
  description = "List of NAT Gateway public IPs"
  value       = aws_eip.nat[*].public_ip
}

#------------------------------------------------------------------------------
# Internet Gateway
#------------------------------------------------------------------------------
output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

#------------------------------------------------------------------------------
# Route Tables
#------------------------------------------------------------------------------
output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "List of private route table IDs"
  value       = aws_route_table.private[*].id
}

#------------------------------------------------------------------------------
# VPC Endpoints
#------------------------------------------------------------------------------
output "s3_vpc_endpoint_id" {
  description = "ID of the S3 VPC Gateway Endpoint"
  value       = aws_vpc_endpoint.s3.id
}

output "s3_vpc_endpoint_prefix_list_id" {
  description = "Prefix list ID for S3 VPC endpoint"
  value       = aws_vpc_endpoint.s3.prefix_list_id
}

output "bedrock_runtime_vpc_endpoint_id" {
  description = "ID of the Bedrock Runtime VPC Interface Endpoint"
  value       = aws_vpc_endpoint.bedrock_runtime.id
}

output "bedrock_vpc_endpoint_id" {
  description = "ID of the Bedrock VPC Interface Endpoint"
  value       = aws_vpc_endpoint.bedrock.id
}

#------------------------------------------------------------------------------
# Security Groups
#------------------------------------------------------------------------------
output "lambda_security_group_id" {
  description = "ID of the Lambda security group"
  value       = aws_security_group.lambda.id
}

output "rds_security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "vpc_endpoints_security_group_id" {
  description = "ID of the VPC endpoints security group"
  value       = aws_security_group.vpc_endpoints.id
}

#------------------------------------------------------------------------------
# Flow Logs
#------------------------------------------------------------------------------
output "vpc_flow_log_id" {
  description = "ID of the VPC Flow Log"
  value       = aws_flow_log.main.id
}

output "vpc_flow_log_cloudwatch_log_group" {
  description = "Name of the CloudWatch Log Group for VPC Flow Logs"
  value       = aws_cloudwatch_log_group.vpc_flow_logs.name
}

#------------------------------------------------------------------------------
# Computed Values
#------------------------------------------------------------------------------
output "azs" {
  description = "List of availability zones used"
  value       = var.availability_zones
}

output "name_prefix" {
  description = "Name prefix used for resources"
  value       = local.name_prefix
}

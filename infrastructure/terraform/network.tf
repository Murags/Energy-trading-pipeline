resource "aws_vpc" "dashboard" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(var.tags, { Name = "${var.name_prefix}-dashboard" })
}

resource "aws_internet_gateway" "dashboard" {
  vpc_id = aws_vpc.dashboard.id
  tags   = var.tags
}

resource "aws_subnet" "dashboard" {
  vpc_id                  = aws_vpc.dashboard.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 1, 0)
  map_public_ip_on_launch = true
  tags                    = merge(var.tags, { Name = "${var.name_prefix}-dashboard-public" })
}

resource "aws_route_table" "dashboard" {
  vpc_id = aws_vpc.dashboard.id
  tags   = var.tags

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.dashboard.id
  }
}

resource "aws_route_table_association" "dashboard" {
  subnet_id      = aws_subnet.dashboard.id
  route_table_id = aws_route_table.dashboard.id
}

resource "aws_security_group" "dashboard" {
  name        = "${var.name_prefix}-dashboard"
  description = "Restrict Streamlit access to the configured reviewer CIDR."
  vpc_id      = aws_vpc.dashboard.id

  ingress {
    description = "Streamlit from reviewer"
    protocol    = "tcp"
    from_port   = 8501
    to_port     = 8501
    cidr_blocks = [var.dashboard_allowed_cidr]
  }

  egress {
    description = "HTTPS access to ECR, S3, and CloudWatch APIs"
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

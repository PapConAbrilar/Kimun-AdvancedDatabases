terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Proveedor principal (Nodo 1)
provider "aws" {
  region = var.aws_region_primary
}

# Proveedor secundario para Global Tables (Nodo 2)
provider "aws" {
  alias  = "replica"
  region = var.aws_region_secondary
}

# ==========================================
# 1. RED (VPC, Subnet, Internet Gateway)
# ==========================================

resource "aws_vpc" "kimun_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "kimun-vpc"
  }
}

resource "aws_internet_gateway" "kimun_igw" {
  vpc_id = aws_vpc.kimun_vpc.id

  tags = {
    Name = "kimun-igw"
  }
}

resource "aws_subnet" "kimun_public_subnet" {
  vpc_id                  = aws_vpc.kimun_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region_primary}a"

  tags = {
    Name = "kimun-public-subnet"
  }
}

resource "aws_route_table" "kimun_rt" {
  vpc_id = aws_vpc.kimun_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.kimun_igw.id
  }

  tags = {
    Name = "kimun-public-rt"
  }
}

resource "aws_route_table_association" "kimun_rta" {
  subnet_id      = aws_subnet.kimun_public_subnet.id
  route_table_id = aws_route_table.kimun_rt.id
}

# ==========================================
# 2. SEGURIDAD (Security Group)
# ==========================================

resource "aws_security_group" "kimun_sg" {
  name        = "kimun-web-sg"
  description = "Permitir trafico HTTP y SSH"
  vpc_id      = aws_vpc.kimun_vpc.id

  ingress {
    description = "HTTP desde cualquier lugar"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH desde cualquier lugar (Solo para el taller)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "kimun-sg"
  }
}

# ==========================================
# 3. COMPUTO (Instancia EC2)
# ==========================================

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical (Ubuntu)

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "kimun_web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.small"
  subnet_id     = aws_subnet.kimun_public_subnet.id
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.kimun_sg.id]

  # IMPORTANTE: En AWS Learner Lab, no podemos crear roles IAM.
  # Usamos el perfil de instancia preexistente "LabInstanceProfile"
  iam_instance_profile = "LabInstanceProfile"

  tags = {
    Name = "Kimun-Web-Server"
  }
}

# ==========================================
# 4. BASE DE DATOS (DynamoDB Global Tables)
# ==========================================

resource "aws_dynamodb_table" "kimun_data" {
  name             = var.dynamodb_table_name
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "PK"
  range_key        = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name               = "GSI1"
    hash_key           = "GSI1PK"
    range_key          = "GSI1SK"
    projection_type    = "ALL"
  }

  # Configuración de Réplica (Tablas Globales - Nodo 2)
  replica {
    region_name = var.aws_region_secondary
  }

  tags = {
    Environment = "Taller-Academico"
  }
}

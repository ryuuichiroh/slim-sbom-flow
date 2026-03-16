resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-vpc-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_1a.id

  tags = {
    Name = "${var.project_name}-vpc-nat-public1-${var.availability_zones[0]}"
  }

  depends_on = [aws_internet_gateway.main]
}

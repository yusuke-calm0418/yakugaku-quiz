# ==========================================
# Compute (EC2 Web Server)
# ==========================================

# 本番AWSの場合のみ最新Amazon Linux 2023 AMIを検索
data "aws_ami" "amazon_linux_2023" {
  count = var.use_ministack ? 0 : 1

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-6.1-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  web_ami_id = var.use_ministack ? var.ministack_ami_id : data.aws_ami.amazon_linux_2023[0].id
}

resource "aws_instance" "web" {
  ami                         = local.web_ami_id
  instance_type               = var.ec2_instance_type
  subnet_id                   = aws_subnet.public_1a.id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  iam_instance_profile        = aws_iam_instance_profile.web.name
  associate_public_ip_address = true
  monitoring                  = false

  # metadata_options {
  #   http_tokens = "required"
  # }

  # root_block_device {
  #   volume_type           = "gp3"
  #   volume_size           = 20
  #   delete_on_termination = true
  #   encrypted             = true

  #   tags = {
  #     Name = "${var.project_name}-root-volume"
  #   }
  # }

  # user_data = <<-EOF
  #             #!/bin/bash
  #             dnf update -y
  #             dnf install -y docker git
  #             systemctl start docker
  #             systemctl enable docker
  #             usermod -a -G docker ec2-user

  #             DOCKER_CONFIG=/usr/local/lib/docker
  #             mkdir -p $DOCKER_CONFIG/cli-plugins
  #             curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64 \
  #               -o $DOCKER_CONFIG/cli-plugins/docker-compose
  #             chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
  #             EOF

  user_data = <<-EOF
            #!/bin/bash
            echo "MiniStack EC2 started"
            EOF

  tags = {
    Name = "${var.project_name}-web-server"
  }
}
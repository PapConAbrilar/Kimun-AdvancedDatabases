output "ec2_public_ip" {
  description = "IP Publica del Servidor Web EC2 (Usa esto para Ansible y para entrar a la App)"
  value       = aws_instance.kimun_web.public_ip
}

output "dynamodb_table_name" {
  description = "Nombre de la Tabla Principal de DynamoDB"
  value       = aws_dynamodb_table.kimun_data.id
}

output "ec2_public_ip" {
  description = "IP Publica del Servidor Web EC2 (Usa esto para Ansible y para entrar a la App)"
  value       = aws_instance.kimun_web.public_ip
}

output "dynamodb_table_name" {
  description = "Nombre de la Tabla Principal de DynamoDB"
  value       = aws_dynamodb_table.kimun_data.id
}

output "s3_analytics_bucket" {
  description = "Bucket S3 para Big Data Analytics"
  value       = aws_s3_bucket.kimun_analytics.id
}

output "athena_workgroup" {
  description = "Workgroup de Athena para consultas KPIs"
  value       = aws_athena_workgroup.kimun_athena.name
}

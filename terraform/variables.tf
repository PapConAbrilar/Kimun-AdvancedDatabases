variable "aws_region_primary" {
  description = "Región principal de AWS (Nodo 1)"
  type        = string
  default     = "us-east-1"
}

variable "aws_region_secondary" {
  description = "Región secundaria para Global Tables (Nodo 2)"
  type        = string
  default     = "us-west-2"
}

variable "key_name" {
  description = "Nombre de la llave SSH registrada en AWS (Ej. vockey)"
  type        = string
  default     = "vockey" # Nombre típico en Learner Labs
}

variable "dynamodb_table_name" {
  description = "Nombre de la tabla de DynamoDB"
  type        = string
  default     = "KimunData-Demo"
}

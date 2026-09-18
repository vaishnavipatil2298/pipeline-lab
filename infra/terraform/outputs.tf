output "postgres_id" {
  description = "Render ID of the managed Postgres instance."
  value       = render_postgres.app.id
}

output "postgres_internal_connection_string" {
  description = "Connection string reachable from services in the same Render region. Use this as DATABASE_URL."
  value       = render_postgres.app.connection_info.internal_connection_string
  sensitive   = true
}

output "postgres_external_connection_string" {
  description = "Connection string reachable from outside Render (for debugging with psql)."
  value       = render_postgres.app.connection_info.external_connection_string
  sensitive   = true
}

output "web_service_url" {
  description = "Public URL of the web service, when Terraform manages it."
  value       = var.manage_web_service ? render_web_service.app[0].url : null
}

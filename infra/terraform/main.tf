provider "render" {
  # Supply these through TF_VAR_render_api_key / TF_VAR_render_owner_id
  # (or RENDER_API_KEY / RENDER_OWNER_ID) env vars — never commit them.
  api_key  = var.render_api_key
  owner_id = var.render_owner_id
}

# The managed Postgres instance. This is the durable replacement for the
# SQLite file that used to live on the web service's ephemeral disk.
resource "render_postgres" "app" {
  name          = var.postgres_name
  plan          = var.postgres_plan
  region        = var.region
  version       = var.postgres_version
  database_name = var.database_name
  database_user = var.database_user
}

# The web service. Optional (count = 0 by default) so this config never
# collides with an already-running manually-created service. Import the
# existing service and flip manage_web_service = true to bring it under
# Terraform, or leave it false and just read the database URL from outputs.
resource "render_web_service" "app" {
  count  = var.manage_web_service ? 1 : 0
  name   = var.service_name
  plan   = var.service_plan
  region = var.region

  health_check_path = "/health"

  env_vars = {
    DATABASE_URL = {
      value = render_postgres.app.connection_info.internal_connection_string
    }
  }

  runtime_source = {
    docker = {
      branch      = var.branch
      repo_url    = var.repo_url
      auto_deploy = true
    }
  }
}

variable "render_api_key" {
  description = "Render API key. Prefer setting the RENDER_API_KEY environment variable instead of committing a value."
  type        = string
  sensitive   = true
  default     = null
}

variable "render_owner_id" {
  description = "Render owner/workspace ID. Prefer setting the RENDER_OWNER_ID environment variable."
  type        = string
  sensitive   = true
  default     = null
}

variable "region" {
  description = "Render region. Must match the region of the existing web service so the internal database URL is reachable."
  type        = string
  default     = "ohio"
}

variable "postgres_name" {
  description = "Name for the managed Postgres instance."
  type        = string
  default     = "pipeline-lab-db"
}

variable "postgres_plan" {
  description = "Render Postgres plan. \"free\" works for the lab; Render free databases expire after 30 days."
  type        = string
  default     = "free"
}

variable "postgres_version" {
  description = "Postgres major version."
  type        = string
  default     = "16"
}

variable "database_name" {
  description = "Name of the logical database created inside the instance."
  type        = string
  default     = "pipeline_lab"
}

variable "database_user" {
  description = "Database user created inside the instance."
  type        = string
  default     = "pipeline_lab"
}

variable "manage_web_service" {
  description = <<-EOT
    Whether Terraform should manage the Render web service as well as the
    database. Leave false until you have imported the existing service
    (`terraform import render_web_service.app <srv-...>`), otherwise Terraform
    would try to create a second service with the same name.
  EOT
  type        = bool
  default     = false
}

variable "service_name" {
  description = "Name of the web service (only used when manage_web_service is true)."
  type        = string
  default     = "pipeline-lab"
}

variable "service_plan" {
  description = "Render web service plan (only used when manage_web_service is true)."
  type        = string
  default     = "free"
}

variable "repo_url" {
  description = "Git repository Render builds from (only used when manage_web_service is true)."
  type        = string
  default     = "https://github.com/vaishnavipatil2298/pipeline-lab"
}

variable "branch" {
  description = "Git branch Render deploys (only used when manage_web_service is true)."
  type        = string
  default     = "main"
}

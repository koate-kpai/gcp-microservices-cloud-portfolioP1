resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "portfolio-repo"
  description   = "Docker repository for microservices"
  format        = "DOCKER"
}

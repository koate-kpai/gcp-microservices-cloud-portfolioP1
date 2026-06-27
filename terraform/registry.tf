resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "portfolio-repo"
  description   = "Docker repository for microservices"
  format        = "DOCKER"
}

# Grant the GKE node service account permission to pull images
resource "google_artifact_registry_repository_iam_member" "gke_sa_reader" {
  location   = google_artifact_registry_repository.repo.location
  repository = google_artifact_registry_repository.repo.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.gke_sa.email}"
}

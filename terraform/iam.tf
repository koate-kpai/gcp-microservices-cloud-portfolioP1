# Workload Identity: Bind Kubernetes ServiceAccounts to GCP ServiceAccounts.
#
# This allows each pod to authenticate to GCP APIs using its Kubernetes
# identity, without managing static service account keys.
#
# Why per-service GSAs:
#   - Each microservice gets only the permissions it needs
#   - The order-service can read Secret Manager (for API key rotation)
#   - The inventory-service has no GCP IAM permissions (uses in-memory storage)
#   - If a pod is compromised, the blast radius is limited to its GSA's roles

# ── Order Service GSA ──────────────────────────────────────────────────────
# Needs: secretmanager.accessor (to read the API key from Secret Manager)
resource "google_service_account" "order_service_sa" {
  account_id   = "order-service-sa"
  display_name = "Order Service Workload Identity SA"
  description  = "GCP SA for order-service pods. Permissions: Secret Manager accessor."
}

resource "google_project_iam_member" "order_service_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.order_service_sa.email}"
}

# Bind the KSA (order-service) to the GSA via Workload Identity.
resource "google_service_account_iam_member" "order_service_wli" {
  service_account_id = google_service_account.order_service_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = format(
    "serviceAccount:%s.svc.id.goog[default/order-service]",
    var.project_id,
  )
}

# ── Inventory Service GSA ──────────────────────────────────────────────────
# Currently needs no GCP permissions (in-memory storage).
# Uncomment and expand when Firestore/Cloud SQL is added.
# resource "google_service_account" "inventory_service_sa" {
#   account_id   = "inventory-service-sa"
#   display_name = "Inventory Service Workload Identity SA"
# }
#
# resource "google_service_account_iam_member" "inventory_service_wli" {
#   service_account_id = google_service_account.inventory_service_sa.name
#   role               = "roles/iam.workloadIdentityUser"
#   member             = format(
#     "serviceAccount:%s.svc.id.goog[default/inventory-service]",
#     var.project_id,
#   )
# }

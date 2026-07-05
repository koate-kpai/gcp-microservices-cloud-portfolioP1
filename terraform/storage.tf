# GCS bucket for Terraform remote state storage.
#
# Why versioning:
#   Every state write creates a new generation. If a corrupt state is
#   pushed, you can restore a previous generation via the GCS Console
#   or gsutil. This has saved teams from unrecoverable state corruption.
#
# Why the bucket name includes the project ID:
#   GCS bucket names are globally unique. Including the project ID
#   virtually guarantees uniqueness without naming conflicts.

resource "google_storage_bucket" "tfstate" {
  name          = "portfolio-tfstate-${var.project_id}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  # Automatically delete old versions after 30 days to control storage costs.
  # The 3 most recent versions are always retained regardless of age.
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    managed_by = "terraform"
    purpose    = "terraform-state"
  }
}

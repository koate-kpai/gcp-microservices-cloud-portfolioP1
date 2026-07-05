# Remote state backend using GCS.
#
# Why GCS over local state:
#   1. Team collaboration: state is shared, not stuck on one machine
#   2. Durability: object versioning provides history and rollback
#   3. Locking: GCS supports state locking via object generation numbers
#
# Migration: after creating the bucket (via storage.tf), run:
#   terraform init -migrate-state
#
# The bucket is created in storage.tf rather than statically defined here
# because Terraform requires the bucket to exist before it can be used as
# a backend. The typical workflow is:
#   1. terraform init (local state)
#   2. terraform apply (creates bucket)
#   3. Uncomment the backend block below
#   4. terraform init -migrate-state (copies state to GCS)

# terraform {
#   backend "gcs" {
#     bucket = "portfolio-tfstate-devops-cloud-portfolio-p1-2026"
#     prefix = "terraform/state"
#   }
# }

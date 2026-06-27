variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The GCP Region"
  type        = string
  default     = "europe-west2" # London (Change if you prefer a different region)
}

variable "zone" {
  description = "The GCP Zone for the GKE cluster"
  type        = string
  default     = "europe-west2-a"
}
#!/usr/bin/env bash
# ============================================================================
# scripts/destroy.sh — Full GCP Resource Teardown (Bash)
# ============================================================================
#
# Purpose:
#   Destroys all GCP resources created by this project in dependency-safe
#   order. Designed for users who clone the repo and want to avoid ongoing
#   cloud charges after evaluation.
#
# Prerequisites:
#   - gcloud CLI authenticated and configured
#   - kubectl connected to the target GKE cluster
#   - terraform installed
#   - jq installed (recommended for JSON parsing)
#
# Usage:
#   ./scripts/destroy.sh
#
#   Optionally override defaults:
#     PROJECT_ID="my-project" ./scripts/destroy.sh
#
# Teardown Order:
#   1. Delete Kubernetes workloads (releases LoadBalancer forwarding rules)
#   2. Delete container images from Artifact Registry
#   3. Run terraform destroy (VPC, GKE, NAT, Artifact Registry repo, SA)
#   4. Optionally delete the Terraform state bucket
# ============================================================================

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────
# Override by exporting these variables before running the script, e.g.:
#   export PROJECT_ID="my-other-project"
#   export ZONE="us-central1-a"

PROJECT_ID="${PROJECT_ID:-devops-cloud-portfolio-p1-2026}"
REGION="${REGION:-europe-west2}"
ZONE="${ZONE:-europe-west2-a}"
GAR_LOCATION="${GAR_LOCATION:-europe-west2-docker.pkg.dev}"
GAR_REPO="${GAR_REPO:-portfolio-repo}"
CLUSTER_NAME="${CLUSTER_NAME:-portfolio-gke-cluster}"
TERRAFORM_DIR="${TERRAFORM_DIR:-terraform}"

echo "══════════════════════════════════════════════════════════════════════"
echo "  GCP Resource Destroyer"
echo "  Project: ${PROJECT_ID}"
echo "  Region:  ${REGION}"
echo "  Zone:    ${ZONE}"
echo "══════════════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  WARNING: This will DESTROY all resources in project ${PROJECT_ID}."
echo "   This action CANNOT be undone."
echo ""

# ── Step 0: Confirmation ──────────────────────────────────────────────────
read -r -p "Are you sure you want to continue? (yes/NO): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
    echo "Aborted."
    exit 0
fi
echo ""

# ── Step 1: Delete Kubernetes workloads ───────────────────────────────────
# Why first: Kubernetes LoadBalancer services create GCP forwarding rules.
# If terraform destroy runs while these exist, the VPC deletion fails
# with "resource in use" errors.
echo "▸ Step 1/4: Deleting Kubernetes workloads..."

# Try to get credentials; if the cluster doesn't exist yet, skip k8s cleanup.
if gcloud container clusters describe "${CLUSTER_NAME}" \
    --zone="${ZONE}" \
    --project="${PROJECT_ID}" \
    > /dev/null 2>&1; then

    # Ensure we have kubeconfig credentials so kubectl can talk to the cluster.
    gcloud container clusters get-credentials "${CLUSTER_NAME}" \
        --zone="${ZONE}" \
        --project="${PROJECT_ID}" \
        --quiet

    # Delete the workloads manifest. This includes Deployments and Services.
    # If the file doesn't exist or resources are already gone, continue.
    if [ -f "k8s/workloads.yaml" ]; then
        kubectl delete -f k8s/workloads.yaml \
            --ignore-not-found \
            --wait=true \
            --timeout=120s 2>&1 || true
        echo "   ✓ Kubernetes workloads deleted"
    else
        echo "   - k8s/workloads.yaml not found, skipping"
    fi

    # Delete any additional K8s resources we created (NetworkPolicies, SAs)
    for manifest in k8s/network-policy.yaml k8s/order-service-sa.yaml k8s/hpa.yaml; do
        if [ -f "${manifest}" ]; then
            kubectl delete -f "${manifest}" --ignore-not-found 2>&1 || true
            echo "   ✓ ${manifest} resources deleted"
        fi
    done
else
    echo "   - GKE cluster not found, skipping Kubernetes cleanup"
fi

# ── Step 2: Delete container images from Artifact Registry ────────────────
# Why: Terraform cannot delete the Artifact Registry repository while images
# still exist inside it. We must purge all images first.
echo ""
echo "▸ Step 2/4: Deleting container images from Artifact Registry..."

# Check if the repository exists before attempting deletion.
REPO_PATH="${GAR_LOCATION}/${PROJECT_ID}/${GAR_REPO}"
if gcloud artifacts repositories describe "${GAR_REPO}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    > /dev/null 2>&1; then

    # List all packages in the repo. For each, delete all versions.
    PACKAGES=$(gcloud artifacts packages list \
        --repository="${GAR_REPO}" \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --format="value(name)" 2>/dev/null || echo "")

    if [ -n "${PACKAGES}" ]; then
        echo "${PACKAGES}" | while IFS= read -r pkg; do
            echo "   Deleting package: ${pkg}"
            # --delete-tags and --quiet skip interactive prompts
            gcloud artifacts versions delete \
                --package="${pkg}" \
                --repository="${GAR_REPO}" \
                --location="${REGION}" \
                --project="${PROJECT_ID}" \
                --delete-tags \
                --quiet 2>&1 || true
        done
        echo "   ✓ All container images deleted"
    else
        echo "   - No packages found in repository"
    fi
else
    echo "   - Artifact Registry repository not found, skipping"
fi

# ── Step 3: Terraform Destroy ─────────────────────────────────────────────
# Why: Terraform manages all remaining GCP resources: GKE cluster, VPC,
# Cloud NAT, Artifact Registry repo, and service accounts.
echo ""
echo "▸ Step 3/4: Running terraform destroy..."

if [ -d "${TERRAFORM_DIR}" ]; then
    pushd "${TERRAFORM_DIR}" > /dev/null

    # We destroy with -auto-approve since the user already confirmed at step 0.
    # If terraform isn't initialised, init first.
    if [ ! -d ".terraform" ]; then
        terraform init -input=false 2>&1 || true
    fi

    terraform destroy \
        -auto-approve \
        -var="project_id=${PROJECT_ID}" \
        -var="region=${REGION}" \
        -var="zone=${ZONE}" \
        2>&1 || {
        echo "   ⚠️  terraform destroy encountered errors. Manual intervention may be needed."
        echo "   See above for details."
    }
    echo "   ✓ Terraform destroy completed"
    popd > /dev/null
else
    echo "   - ${TERRAFORM_DIR} directory not found, skipping terraform destroy"
fi

# ── Step 4: Optionally delete the Terraform state bucket ──────────────────
# Why: The GCS state bucket persists after terraform destroy (it manages its
# own lifecycle). We ask the user if they'd like to delete it too.
echo ""
echo "▸ Step 4/4: Terraform state bucket cleanup..."

TFSTATE_BUCKET="portfolio-tfstate-${PROJECT_ID}"
if gsutil ls "gs://${TFSTATE_BUCKET}" > /dev/null 2>&1; then
    echo ""
    echo "   A Terraform state bucket (gs://${TFSTATE_BUCKET}) still exists."
    echo "   It contains the state history and is NOT deleted by terraform destroy."
    echo ""
    read -r -p "   Delete the state bucket? (yes/NO): " DELETE_BUCKET
    if [ "${DELETE_BUCKET}" = "yes" ]; then
        # Object versioning may be enabled; delete all versions + the bucket
        gsutil rm -r "gs://${TFSTATE_BUCKET}" 2>&1 || true
        echo "   ✓ Terraform state bucket deleted"
    else
        echo "   - Skipped. Bucket gs://${TFSTATE_BUCKET} retains state history."
        echo "     Delete manually: gsutil rm -r gs://${TFSTATE_BUCKET}"
    fi
else
    echo "   - No state bucket found (or bucket doesn't follow naming convention)"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════════"
echo "  Teardown complete."
echo ""
echo "  Next steps:"
echo "  1. Verify in GCP Console that all resources are gone:"
echo "     https://console.cloud.google.com/kubernetes/list"
echo "     https://console.cloud.google.com/networking/nat"
echo "     https://console.cloud.google.com/artifacts"
echo ""
echo "  2. Check for any orphaned LoadBalancer forwarding rules:"
echo "     gcloud compute forwarding-rules list --project=${PROJECT_ID}"
echo ""
echo "  3. Check for any orphaned disks (GKE may leave PVs behind):"
echo "     gcloud compute disks list --project=${PROJECT_ID}"
echo ""
echo "  If you want to redeploy, you must first re-run:"
echo "     cd terraform && terraform init && terraform apply"
echo "══════════════════════════════════════════════════════════════════════"

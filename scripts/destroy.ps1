<#
.SYNOPSIS
    Full GCP Resource Teardown (PowerShell)

.DESCRIPTION
    Destroys all GCP resources created by this project in dependency-safe order.
    Mirrors the logic of scripts/destroy.sh for Windows/Cloud Shell users.

    Teardown Order:
      1. Delete Kubernetes workloads (releases LoadBalancer forwarding rules)
      2. Delete container images from Artifact Registry
      3. Run terraform destroy (VPC, GKE, NAT, Artifact Registry repo, SA)
      4. Optionally delete the Terraform state bucket

.PARAMETER ProjectId
    GCP Project ID (default: devops-cloud-portfolio-p1-2026)

.PARAMETER Region
    GCP Region (default: europe-west2)

.PARAMETER Zone
    GCP Zone (default: europe-west2-a)

.PARAMETER Confirm
    Skip confirmation prompt (useful in automation scripts)

.EXAMPLE
    .\scripts\destroy.ps1

.EXAMPLE
    .\scripts\destroy.ps1 -ProjectId "my-project" -Confirm

.NOTES
    Requires: gcloud CLI, kubectl, terraform and gsutil installed and authenticated.
#>

param(
    [string]$ProjectId = "devops-cloud-portfolio-p1-2026",
    [string]$Region    = "europe-west2",
    [string]$Zone      = "europe-west2-a",
    [switch]$Confirm
)

$GARLocation = "europe-west2-docker.pkg.dev"
$GARRepo     = "portfolio-repo"
$ClusterName = "portfolio-gke-cluster"
$TerraformDir = "terraform"

Write-Host "══════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  GCP Resource Destroyer (PowerShell)" -ForegroundColor Cyan
Write-Host "  Project: $ProjectId" -ForegroundColor Cyan
Write-Host "  Region:  $Region" -ForegroundColor Cyan
Write-Host "  Zone:    $Zone" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  WARNING: This will DESTROY all resources in project ${ProjectId}." -ForegroundColor Red
Write-Host "   This action CANNOT be undone." -ForegroundColor Red
Write-Host ""

# ── Step 0: Confirmation ──────────────────────────────────────────────────
if (-not $Confirm) {
    $response = Read-Host "Are you sure you want to continue? (yes/NO)"
    if ($response -ne "yes") {
        Write-Host "Aborted."
        exit 0
    }
}
Write-Host ""

# ── Step 1: Delete Kubernetes workloads ───────────────────────────────────
# Why first: K8s LoadBalancer Services create GCP forwarding rules. If
# terraform destroy runs while these exist, the VPC deletion fails.
Write-Host "▸ Step 1/4: Deleting Kubernetes workloads..."

# Check if the GKE cluster exists.
$clusterExists = $false
try {
    $null = gcloud container clusters describe $ClusterName `
        --zone=$Zone `
        --project=$ProjectId `
        --quiet 2>$null
    $clusterExists = $true
} catch {
    $clusterExists = $false
}

if ($clusterExists) {
    # Get kubeconfig credentials
    gcloud container clusters get-credentials $ClusterName `
        --zone=$Zone `
        --project=$ProjectId `
        --quiet 2>&1 | Out-Null

    # Delete the main workloads manifest.
    $workloadsPath = Join-Path -Path (Get-Location) -ChildPath "k8s\workloads.yaml"
    if (Test-Path $workloadsPath) {
        kubectl delete -f $workloadsPath `
            --ignore-not-found `
            --wait=true `
            --timeout=120s 2>&1 | Out-Null
        Write-Host "   ✓ Kubernetes workloads deleted"
    } else {
        Write-Host "   - k8s/workloads.yaml not found, skipping"
    }

    # Delete any additional K8s resources.
    $extraManifests = @("k8s\network-policy.yaml", "k8s\order-service-sa.yaml", "k8s\hpa.yaml")
    foreach ($mf in $extraManifests) {
        $mfPath = Join-Path -Path (Get-Location) -ChildPath $mf
        if (Test-Path $mfPath) {
            kubectl delete -f $mfPath --ignore-not-found 2>&1 | Out-Null
            Write-Host "   ✓ $mf resources deleted"
        }
    }
} else {
    Write-Host "   - GKE cluster not found, skipping Kubernetes cleanup"
}

# ── Step 2: Delete container images from Artifact Registry ────────────────
# Why: Terraform cannot delete the Artifact Registry repo while images exist.
Write-Host ""
Write-Host "▸ Step 2/4: Deleting container images from Artifact Registry..."

$repoExists = $false
try {
    $null = gcloud artifacts repositories describe $GARRepo `
        --location=$Region `
        --project=$ProjectId `
        --quiet 2>$null
    $repoExists = $true
} catch {
    $repoExists = $false
}

if ($repoExists) {
    # List packages and delete all versions.
    $packages = gcloud artifacts packages list `
        --repository=$GARRepo `
        --location=$Region `
        --project=$ProjectId `
        --format="value(name)" 2>$null

    if ($packages) {
        foreach ($pkg in $packages) {
            Write-Host "   Deleting package: $pkg"
            gcloud artifacts versions delete `
                --package="$pkg" `
                --repository=$GARRepo `
                --location=$Region `
                --project=$ProjectId `
                --delete-tags `
                --quiet 2>&1 | Out-Null
        }
        Write-Host "   ✓ All container images deleted"
    } else {
        Write-Host "   - No packages found in repository"
    }
} else {
    Write-Host "   - Artifact Registry repository not found, skipping"
}

# ── Step 3: Terraform Destroy ─────────────────────────────────────────────
Write-Host ""
Write-Host "▸ Step 3/4: Running terraform destroy..."

$tfDir = Join-Path -Path (Get-Location) -ChildPath $TerraformDir
if (Test-Path $tfDir) {
    Push-Location $tfDir

    # Ensure terraform is initialised.
    $terraformDirCheck = Join-Path -Path $tfDir -ChildPath ".terraform"
    if (-not (Test-Path $terraformDirCheck)) {
        terraform init -input=false 2>&1 | Out-Null
    }

    terraform destroy `
        -auto-approve `
        -var="project_id=$ProjectId" `
        -var="region=$Region" `
        -var="zone=$Zone" 2>&1 | Write-Host

    Write-Host "   ✓ Terraform destroy completed"
    Pop-Location
} else {
    Write-Host "   - $TerraformDir directory not found, skipping terraform destroy"
}

# ── Step 4: Optionally delete the Terraform state bucket ──────────────────
Write-Host ""
Write-Host "▸ Step 4/4: Terraform state bucket cleanup..."

$tfstateBucket = "portfolio-tfstate-${ProjectId}"

try {
    $null = gsutil ls "gs://${tfstateBucket}" 2>$null
    $bucketExists = $true
} catch {
    $bucketExists = $false
}

if ($bucketExists) {
    Write-Host ""
    Write-Host "   A Terraform state bucket (gs://${tfstateBucket}) still exists." -ForegroundColor Yellow
    Write-Host "   It contains the state history and is NOT deleted by terraform destroy." -ForegroundColor Yellow
    Write-Host ""
    $deleteBucket = Read-Host "   Delete the state bucket? (yes/NO)"
    if ($deleteBucket -eq "yes") {
        gsutil rm -r "gs://${tfstateBucket}" 2>&1 | Out-Null
        Write-Host "   ✓ Terraform state bucket deleted"
    } else {
        Write-Host "   - Skipped. Bucket gs://${tfstateBucket} retains state history."
        Write-Host "     Delete manually: gsutil rm -r gs://${tfstateBucket}"
    }
} else {
    Write-Host "   - No state bucket found (or bucket doesn't follow naming convention)"
}

# ── Summary ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Teardown complete." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Green
Write-Host "  1. Verify in GCP Console that all resources are gone:"
Write-Host "     https://console.cloud.google.com/kubernetes/list"
Write-Host "     https://console.cloud.google.com/networking/nat"
Write-Host "     https://console.cloud.google.com/artifacts"
Write-Host ""
Write-Host "  2. Check for any orphaned LoadBalancer forwarding rules:"
Write-Host "     gcloud compute forwarding-rules list --project=$ProjectId"
Write-Host ""
Write-Host "  3. Check for any orphaned disks (GKE may leave PVs behind):"
Write-Host "     gcloud compute disks list --project=$ProjectId"
Write-Host ""
Write-Host "  If you want to redeploy, you must first re-run:"
Write-Host "     cd terraform && terraform init && terraform apply"
Write-Host "══════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

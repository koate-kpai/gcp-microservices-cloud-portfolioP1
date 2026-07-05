# GCP Microservices Cloud Portfolio

Two FastAPI microservices (order-service + inventory-service) deployed to a private GKE cluster on GCP. Built as a cloud portfolio project demonstrating infrastructure-as-code, CI/CD, observability, and security best practices.

## Architecture

```
  Client ──► LoadBalancer ──► Order Service ──► Inventory Service
                                (port 8000)       (port 8001)
```

- **Order Service** — Public API gateway. Accepts orders, calls inventory, persists to in-memory store.
- **Inventory Service** — Internal backend. Manages product catalog and stock reservations.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Google Cloud CLI (`gcloud`) — authenticated with your project
- Terraform 1.5+
- kubectl

## Quick Start

### Local development (Docker Compose)

```bash
docker compose up --build
```

- Order service: http://localhost:8000
- Inventory service: http://localhost:8001
- API docs: http://localhost:8000/docs

### Running tests

```bash
# Install dependencies
pip install -r src/inventory-service/requirements.txt
pip install -r src/order-service/requirements.txt
pip install pytest

# Run all tests
pytest

# Run by service
pytest src/inventory-service/tests
pytest src/order-service/tests

# Run integration tests only
pytest src/order-service/tests/integration
```

## Project Structure

```
.
├── .github/workflows/
│   ├── deploy.yml          # Build & deploy to GKE (on push to main)
│   └── pr-checks.yml       # Lint, test, build (on PR)
├── k8s/
│   ├── workloads.yaml      # Deployments, Services, resource limits
│   ├── hpa.yaml            # HorizontalPodAutoscaler (CPU-based)
│   ├── network-policy.yaml # Zero-trust pod networking
│   └── order-service-sa.yaml
├── scripts/
│   ├── destroy.sh          # Full teardown (bash)
│   └── destroy.ps1         # Full teardown (PowerShell)
├── src/
│   ├── inventory-service/  # FastAPI (port 8001)
│   └── order-service/      # FastAPI (port 8000)
├── terraform/
│   ├── main.tf             # Provider config
│   ├── vpc.tf              # VPC, subnet, Cloud NAT
│   ├── gke.tf              # Private GKE cluster, spot node pool
│   ├── registry.tf         # Artifact Registry + IAM
│   ├── storage.tf          # GCS bucket for Terraform state
│   ├── iam.tf              # Workload Identity bindings
│   └── variables.tf        # Input variables
├── docker-compose.yml
├── pyproject.toml
└── .pre-commit-config.yaml
```

## Deploy to GKE

The CI/CD pipeline (`.github/workflows/deploy.yml`) handles deployment automatically on every push to `main`. It:

1. Authenticates via Workload Identity Federation
2. Builds and pushes Docker images to Artifact Registry (tagged with commit SHA)
3. Injects image tags into `k8s/workloads.yaml`
4. Applies manifests with `kubectl apply`
5. Verifies rollout with debug output on failure

### Infrastructure provisioning

```bash
cd terraform
terraform init
terraform apply -auto-approve
```

### Manual deployment

```bash
# Build and push
docker build -t europe-west2-docker.pkg.dev/devops-cloud-portfolio-p1-2026/portfolio-repo/order-service:latest src/order-service
docker push europe-west2-docker.pkg.dev/devops-cloud-portfolio-p1-2026/portfolio-repo/order-service:latest

# Repeat for inventory-service, then:
kubectl apply -f k8s/
```

## Cost Management

This project runs on real GCP resources and incurs ongoing costs (~$55-65/month for GKE + Cloud NAT). To avoid charges when not in use, run the teardown script.

### Bash (Linux / macOS / Cloud Shell)

```bash
./scripts/destroy.sh
```

### PowerShell (Windows)

```powershell
.\scripts\destroy.ps1
```

### What gets destroyed

1. Kubernetes workloads (Deployments, Services, HPAs, NetworkPolicies)
2. Container images in Artifact Registry
3. All Terraform-managed resources (GKE cluster, VPC, Cloud NAT, IAM)
4. Optionally: Terraform state bucket

### Manual cleanup

```bash
# Check for orphaned forwarding rules
gcloud compute forwarding-rules list --project=devops-cloud-portfolio-p1-2026

# Check for orphaned disks
gcloud compute disks list --project=devops-cloud-portfolio-p1-2026
```

## CI/CD Pipeline

| Event | Workflow | Actions |
|---|---|---|
| Push to `main` | `deploy.yml` | Build, push, deploy to GKE |
| PR to `main` | `pr-checks.yml` | Ruff lint, pytest, Docker build |

## Technology Decisions

- **FastAPI** — Async Python framework with automatic OpenAPI docs and Pydantic validation
- **In-memory persistence** — Zero-cost data layer using the repository pattern. Swap to Firestore/Cloud SQL without changing route handlers
- **Prometheus /metrics** — Application-level metrics scrapable by GKE Managed Prometheus or kube-prometheus-stack
- **API key auth** — Free alternative to IAP/OAuth2 for a portfolio project.
- **Spot (preemptible) nodes** — 60-90% discount; safe with 2+ replicas for HA
- **Private cluster** — Nodes have no public IPs; all egress through Cloud NAT

## License

MIT

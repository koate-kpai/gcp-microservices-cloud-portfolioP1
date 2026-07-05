"""Prometheus metrics for the inventory-service.

Exposes counters and histograms that can be scraped by Prometheus
(or GKE Managed Prometheus) for cluster-wide observability.

Why /metrics at the application level (not a sidecar):
  - Zero additional infrastructure
  - Scraped directly by kube-prometheus-stack or GKE Managed Prometheus
  - Can be extended with business metrics (inventory levels, reservation rates)
"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

http_request_count = Counter(
    "inventory_http_requests_total",
    "Total HTTP requests to inventory-service",
    ["method", "endpoint", "status"],
)

http_request_latency = Histogram(
    "inventory_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

reservations_total = Counter(
    "inventory_reservations_total",
    "Total inventory reservation attempts",
    ["status"],
)

inventory_items_total = Counter(
    "inventory_items_checked_total",
    "Total inventory item lookups (individual item checks)",
)


async def metrics_endpoint():
    """Return Prometheus-format metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

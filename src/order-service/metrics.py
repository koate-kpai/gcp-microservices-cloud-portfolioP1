"""Prometheus metrics for the order-service.

Exposes application-level metrics for Prometheus scraping.
Kept in a separate module to avoid cluttering main.py with
instrumentation code.
"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

http_request_count = Counter(
    "order_http_requests_total",
    "Total HTTP requests to order-service",
    ["method", "endpoint", "status"],
)

http_request_latency = Histogram(
    "order_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

orders_created_total = Counter(
    "order_orders_created_total",
    "Total orders created",
    ["status"],
)


async def metrics_endpoint():
    """Return Prometheus-format metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

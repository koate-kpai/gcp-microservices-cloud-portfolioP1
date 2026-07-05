"""API key authentication middleware for order-service.

Why API keys over IAP or OAuth2:
  - IAP costs $0.05/user/session (~$4-5/month even for one user)
  - OAuth2-proxy requires additional infrastructure to deploy and maintain
  - A static API key is free, simple, and sufficient for a portfolio/Demo project

Security considerations:
  - The key is sent as an X-API-Key header (must be paired with HTTPS)
  - Key rotation is manual (update env var, restart pods)
  - For production, load the key from GCP Secret Manager via Workload Identity
"""

import os
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates the X-API-Key header against the configured key.

    If no API key is configured (empty string), authentication is skipped
    entirely. This allows the service to run without a key in development
    or when the key hasn't been provisioned yet.

    Excludes health, ready, and metrics endpoints from authentication
    so that Kubernetes probes and Prometheus scraping work without a key.
    """

    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        # Allow unauthenticated access to operational endpoints.
        if request.url.path in ("/healthz", "/ready", "/metrics"):
            return await call_next(request)

        # If no key is configured, skip auth (safe default for dev).
        if not self.api_key:
            return await call_next(request)

        # Extract and validate the API key.
        provided = request.headers.get("X-API-Key", "")
        if not provided or provided != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid API key. Provide X-API-Key header.",
            )

        return await call_next(request)

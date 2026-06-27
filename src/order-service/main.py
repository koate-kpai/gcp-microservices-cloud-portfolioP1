# order-service/main.py

import time
import json
import uuid
import logging
import sys
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
import httpx

from config import settings
from schemas import OrderCreate, OrderResponse

# Set up structured JSON logging for GCP Cloud Logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("order-service")


def log_json(severity: str, message: str, extra: dict = None):
    log_data = {
        "severity": severity,
        "message": message,
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
    }
    if extra:
        log_data.update(extra)
    logger.info(json.dumps(log_data))


app = FastAPI(title=settings.PROJECT_NAME)

# Global HTTPX async client for connection pooling
async_client = httpx.AsyncClient(timeout=5.0)


@app.on_event("shutdown")
async def shutdown_event():
    await async_client.aclose()


# Middleware for structured request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    log_json(
        "INFO",
        "HTTP Request Processed",
        {
            "http.method": request.method,
            "http.url": str(request.url),
            "http.status_code": response.status_code,
            "http.duration_sec": duration,
        },
    )
    return response


# Liveness Probe
@app.get("/healthz", status_code=status.HTTP_200_OK)
async def liveness():
    return {"status": "healthy"}


# Readiness Probe
@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness():
    # Verify downstream dependency availability if critical
    return {"status": "ready"}


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_order(order: OrderCreate):
    order_id = uuid.uuid4()
    total_amount = sum(item.price * item.quantity for item in order.items)

    log_json("INFO", f"Processing new order {order_id}", {"order_id": str(order_id)})

    # Forward payload asynchronously to internal Inventory Service
    try:
        inventory_payload = {
            "order_id": str(order_id),
            "items": [item.dict() for item in order.items],
        }
        response = await async_client.post(
            f"{settings.INVENTORY_SERVICE_URL}/inventory/reserve",
            json=inventory_payload,
        )

        if response.status_code != 200:
            log_json(
                "ERROR",
                f"Inventory reservation failed for order {order_id}",
                {"status_code": response.status_code},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to clear inventory verification.",
            )

    except httpx.RequestError as exc:
        log_json("CRITICAL", f"Network error connecting to inventory service: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inventory service unreachable.",
        )

    return OrderResponse(
        order_id=order_id,
        status="accepted_and_reserved",
        total_amount=round(total_amount, 2),
    )

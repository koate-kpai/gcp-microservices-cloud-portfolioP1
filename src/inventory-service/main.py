# inventory-service/main.py

import time
import json
import logging
import sys
from fastapi import FastAPI, status, Request
from config import settings
from schemas import InventoryReservationRequest, ReservationResponse

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("inventory-service")


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


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def liveness():
    return {"status": "healthy"}


@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness():
    return {"status": "ready"}


@app.post(
    "/inventory/reserve",
    response_model=ReservationResponse,
    status_code=status.HTTP_200_OK,
)
async def reserve_inventory(payload: InventoryReservationRequest):
    log_json(
        "INFO",
        f"Checking stock availability for order {payload.order_id}",
        {"order_id": payload.order_id},
    )

    # Simulate database inventory check logic
    # Real implementations would fetch data here; we assume success for mock production flow
    log_json(
        "INFO",
        f"Inventory locked successfully for order {payload.order_id}",
        {"order_id": payload.order_id},
    )

    return ReservationResponse(
        order_id=payload.order_id, reservation_status="success", success=True
    )

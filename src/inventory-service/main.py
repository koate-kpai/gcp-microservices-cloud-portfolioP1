import time
import json
import logging
import sys
from fastapi import FastAPI, HTTPException, status, Request
from config import settings
from schemas import InventoryReservationRequest, ReservationResponse, Item
from inventory_repo import InventoryRepo

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

# Repository instance — scoped to the application lifetime.
# Swap this for a database-backed implementation without changing routes.
inventory = InventoryRepo()


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


@app.get("/items", response_model=list[Item], status_code=status.HTTP_200_OK)
async def list_items():
    return inventory.list_items()


@app.get("/items/{item_id}", response_model=Item, status_code=status.HTTP_200_OK)
async def get_item(item_id: str):
    item = inventory.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


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

    # Delegate to the repository which performs the actual stock check.
    items_for_repo = [r.model_dump() for r in payload.items]
    success = inventory.reserve(payload.order_id, items_for_repo)

    if not success:
        log_json(
            "WARNING",
            f"Insufficient stock for order {payload.order_id}",
            {"order_id": payload.order_id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient stock for one or more items",
        )

    log_json(
        "INFO",
        f"Inventory locked successfully for order {payload.order_id}",
        {"order_id": payload.order_id},
    )

    return ReservationResponse(
        order_id=payload.order_id, reservation_status="success", success=True
    )

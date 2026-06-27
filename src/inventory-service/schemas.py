# inventory-service/schemas.py

from pydantic import BaseModel, Field
from typing import List


class ReservedItem(BaseModel):
    item_id: str
    quantity: int


class InventoryReservationRequest(BaseModel):
    order_id: str
    items: List[ReservedItem]


class ReservationResponse(BaseModel):
    order_id: str
    reservation_status: str
    success: bool

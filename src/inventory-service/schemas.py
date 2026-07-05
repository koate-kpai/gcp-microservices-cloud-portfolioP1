from pydantic import BaseModel, Field
from typing import List, Optional


class Item(BaseModel):
    """A product in the inventory catalog."""
    item_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., ge=0, description="Current stock level")
    price: float = Field(..., gt=0.0, description="Unit price in GBP")


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

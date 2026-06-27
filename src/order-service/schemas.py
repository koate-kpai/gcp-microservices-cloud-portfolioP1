# order-service/schemas.py

from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from typing import List


class OrderItem(BaseModel):
    item_id: str = Field(..., min_length=3, max_length=50, examples=["item-prod-102"])
    quantity: int = Field(..., gt=0, le=100, examples=[2])
    price: float = Field(..., gt=0.0, examples=[29.99])


class OrderCreate(BaseModel):
    customer_email: EmailStr = Field(
        ..., examples=["engineering-candidate@example.com"]
    )
    items: List[OrderItem] = Field(..., min_items=1)


class OrderResponse(BaseModel):
    order_id: UUID
    status: str
    total_amount: float

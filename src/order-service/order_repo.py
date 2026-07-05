"""In-memory order repository.

Follows the same repository pattern as inventory-service. Data access is
isolated behind this class so that a future database swap affects only
this file, not the route handlers or schemas.

Why in-memory:
  - Consistent with inventory-service approach
  - No additional infrastructure required
  - Data persists for the lifetime of the process
Trade-off:
  - Orders are lost on pod restart
  - Acceptable for portfolio/demo; production would persist to a database
"""

import time
import logging
from uuid import UUID
from typing import List

logger = logging.getLogger("order-repo")


class OrderRepo:
    """Manages orders in memory."""

    def __init__(self):
        self._orders: dict[str, dict] = {}

    def create(self, order_id: UUID, total_amount: float, status: str = "accepted_and_reserved") -> dict:
        """Store a new order and return its representation."""
        entry = {
            "order_id": str(order_id),
            "status": status,
            "total_amount": round(total_amount, 2),
            "created_at": time.time(),
        }
        self._orders[str(order_id)] = entry
        logger.info("Order %s created with total %.2f", order_id, total_amount)
        return dict(entry)

    def get(self, order_id: str) -> dict | None:
        """Retrieve a single order by ID, or None."""
        entry = self._orders.get(order_id)
        if entry:
            return dict(entry)
        return None

    def list(self) -> List[dict]:
        """Return all orders, newest first."""
        entries = sorted(
            self._orders.values(),
            key=lambda o: o["created_at"],
            reverse=True,
        )
        return [dict(e) for e in entries]

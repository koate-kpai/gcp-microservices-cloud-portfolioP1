"""In-memory inventory repository.

Implements the repository pattern to isolate data access logic from
route handlers. This allows swapping the backend storage (e.g., to
Firestore) by changing only this file — the API layer stays untouched.

Why in-memory:
  - Zero infrastructure cost (no DB provisioning)
  - Fastest possible local development
  - Proves the API contract before committing to a database
Trade-off:
  - Data is ephemeral (lost on pod restart)
  - Acceptable at this stage; production would use Firestore/Cloud SQL
"""

import time
import logging

logger = logging.getLogger("inventory-repo")


class InventoryRepo:
    """Manages inventory items and reservations in memory."""

    def __init__(self):
        self._items: dict[str, dict] = {}
        self._reservations: dict[str, list[dict]] = {}
        self._seed()

    def _seed(self) -> None:
        """Populate a default catalog so the API has data to work with."""
        defaults = [
            {"item_id": "item-prod-101", "name": "Widget Alpha", "quantity": 50, "price": 19.99},
            {"item_id": "item-prod-102", "name": "Gadget Beta",  "quantity": 30, "price": 29.99},
            {"item_id": "item-prod-103", "name": "Doohickey Gamma","quantity": 100,"price": 9.99},
            {"item_id": "item-prod-104", "name": "Thingamajig Delta","quantity": 20,"price": 49.99},
        ]
        for item in defaults:
            self._items[item["item_id"]] = dict(item)
        logger.info("Seeded %d inventory items", len(defaults))

    def get_item(self, item_id: str) -> dict | None:
        """Return a single item or None if not found."""
        item = self._items.get(item_id)
        if item:
            return dict(item)  # return a copy to prevent external mutation
        return None

    def list_items(self) -> list[dict]:
        """Return all catalog items."""
        return [dict(item) for item in self._items.values()]

    def reserve(self, order_id: str, items: list[dict]) -> bool:
        """Reserve stock for a set of items.

        Returns True if all items are available and reservation succeeds.
        Returns False if any item is out of stock or doesn't exist.
        On failure, no stock is modified (atomic-check, no partial reserve).
        """

        # Phase 1: Validate that all items exist and have sufficient stock.
        for req in items:
            item = self._items.get(req["item_id"])
            if item is None:
                logger.warning("Reservation failed: item %s not found", req["item_id"])
                return False
            if item["quantity"] < req["quantity"]:
                logger.warning(
                    "Reservation failed: insufficient stock for %s "
                    "(requested %d, available %d)",
                    req["item_id"], req["quantity"], item["quantity"],
                )
                return False

        # Phase 2: Deduct stock (all checks passed).
        for req in items:
            item = self._items[req["item_id"]]
            item["quantity"] -= req["quantity"]
            item["last_updated"] = time.time()

        # Phase 3: Record the reservation for future release/rollback.
        self._reservations[order_id] = [dict(r) for r in items]
        logger.info("Reservation succeeded for order %s", order_id)
        return True

    def release(self, order_id: str) -> bool:
        """Release a previously made reservation, restoring stock.

        This exists for future-proofing (e.g., cancelled orders).
        Currently not exposed via API but completes the repository interface.
        """
        reserved = self._reservations.pop(order_id, None)
        if reserved is None:
            return False
        for req in reserved:
            item = self._items.get(req["item_id"])
            if item:
                item["quantity"] += req["quantity"]
        logger.info("Released reservation for order %s", order_id)
        return True

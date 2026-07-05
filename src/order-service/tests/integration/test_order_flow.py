"""Integration-level tests for the order-service.

Validates that the order creation flow handles inventory responses
correctly. The inventory-service is mocked via respx so these tests
run without external dependencies.
"""

import pytest
import respx
from httpx import Response
from fastapi.testclient import TestClient

from main import app, orders
from config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_orders():
    """Clear the order repo before each test for full isolation."""
    orders._orders.clear()
    yield


class TestInventoryErrors:
    def test_returns_502_when_inventory_returns_error_status(self):
        """Order returns 502 when inventory responds with a non-200 status."""
        reserve_url = f"{settings.INVENTORY_SERVICE_URL}/inventory/reserve"

        with respx.mock() as respx_mock:
            respx_mock.post(reserve_url).respond(500, json={"detail": "Internal error"})

            payload = {
                "customer_email": "buyer@example.com",
                "items": [{"item_id": "item-prod-101", "quantity": 1, "price": 10.0}],
            }
            response = client.post("/orders", json=payload)
            assert response.status_code == 502

    def test_returns_502_when_inventory_returns_conflict(self):
        """Order returns 502 when inventory returns 409 (insufficient stock)."""
        reserve_url = f"{settings.INVENTORY_SERVICE_URL}/inventory/reserve"

        with respx.mock() as respx_mock:
            respx_mock.post(reserve_url).respond(
                409, json={"detail": "Insufficient stock"}
            )

            payload = {
                "customer_email": "buyer@example.com",
                "items": [{"item_id": "item-prod-101", "quantity": 1, "price": 10.0}],
            }
            response = client.post("/orders", json=payload)
            assert response.status_code == 502

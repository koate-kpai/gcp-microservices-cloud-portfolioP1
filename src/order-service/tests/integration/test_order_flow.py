"""Integration-level tests for the order-service.

Validates that the order creation flow handles inventory responses
correctly. The inventory-service is mocked via respx (see conftest.py)
so these tests run without external dependencies.

This file exists as a separate integration test directory to distinguish
pure unit tests from tests that validate the service-to-service contract.
The naming convention (test_order_flow vs test_orders) makes it easy to
run each category independently:
  pytest src/order-service/tests/integration/
  pytest src/order-service/tests/ -k "not integration"
"""

import respx
from httpx import Response
from fastapi.testclient import TestClient

from main import app
from config import settings
from order_repo import OrderRepo

client = TestClient(app)
orders = OrderRepo()


def test_inventory_service_unreachable():
    """Order creation returns 503 when inventory is unreachable."""
    reserve_url = f"{settings.INVENTORY_SERVICE_URL}/inventory/reserve"

    with respx.mock() as respx_mock:
        respx_mock.post(reserve_url).mock(side_effect=ConnectionError("Connection refused"))

        payload = {
            "customer_email": "buyer@example.com",
            "items": [{"item_id": "item-prod-101", "quantity": 1, "price": 10.0}],
        }
        response = client.post("/orders", json=payload)
        assert response.status_code == 503


def test_inventory_service_returns_non_200():
    """Order creation returns 502 when inventory returns a non-200 status."""
    reserve_url = f"{settings.INVENTORY_SERVICE_URL}/inventory/reserve"

    with respx.mock() as respx_mock:
        respx_mock.post(reserve_url).respond(500, json={"detail": "Internal error"})

        payload = {
            "customer_email": "buyer@example.com",
            "items": [{"item_id": "item-prod-101", "quantity": 1, "price": 10.0}],
        }
        response = client.post("/orders", json=payload)
        assert response.status_code == 502

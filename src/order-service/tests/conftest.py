"""Shared fixtures for order-service tests.

Uses respx to mock HTTP calls to the inventory service so tests
don't require the downstream service to be running.
"""

import pytest
import respx
from httpx import Response

from main import app
from config import settings


@pytest.fixture(autouse=True)
def mock_inventory_service():
    """Mock all outbound HTTP calls to inventory-service."""
    with respx.mock(assert_all_called=False) as respx_mock:
        reserve_url = f"{settings.INVENTORY_SERVICE_URL}/inventory/reserve"
        respx_mock.post(reserve_url).respond(
            status_code=200,
            json={"order_id": "mock", "reservation_status": "success", "success": True},
        )
        yield respx_mock

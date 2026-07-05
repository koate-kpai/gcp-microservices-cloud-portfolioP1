"""Configure Python path and shared fixtures for order-service tests."""

import sys
from pathlib import Path

import pytest
import respx
from httpx import Response

# Add the parent service directory to sys.path so that
# `from main import app` works during test collection.
SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


@pytest.fixture
def inventory_mock():
    """Mock inventory-service /inventory/reserve to return 200.

    Usage in a test:
        def test_something(inventory_mock):
            ...
    """
    from config import settings

    with respx.mock(assert_all_called=False) as respx_mock:
        reserve_url = f"{settings.INVENTORY_SERVICE_URL}/inventory/reserve"
        respx_mock.post(reserve_url).respond(
            status_code=200,
            json={"order_id": "mock", "reservation_status": "success", "success": True},
        )
        yield respx_mock

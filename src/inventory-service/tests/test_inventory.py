"""Tests for the inventory-service API endpoints."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


class TestListItems:
    def test_returns_seeded_items(self):
        response = client.get("/items")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert data[0]["item_id"] == "item-prod-101"
        assert data[0]["name"] == "Widget Alpha"
        assert data[0]["quantity"] == 50
        assert data[0]["price"] == 19.99


class TestGetItem:
    def test_existing_item(self):
        response = client.get("/items/item-prod-102")
        assert response.status_code == 200
        assert response.json()["name"] == "Gadget Beta"

    def test_missing_item(self):
        response = client.get("/items/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Item not found"


class TestReserveInventory:
    def test_reserve_success(self):
        payload = {
            "order_id": "test-order-1",
            "items": [{"item_id": "item-prod-101", "quantity": 2}],
        }
        response = client.post("/inventory/reserve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "test-order-1"
        assert data["reservation_status"] == "success"
        assert data["success"] is True

        # Verify stock was deducted
        item = client.get("/items/item-prod-101").json()
        assert item["quantity"] == 48  # 50 - 2

    def test_reserve_insufficient_stock(self):
        # Try to reserve more than available
        payload = {
            "order_id": "test-order-2",
            "items": [{"item_id": "item-prod-104", "quantity": 999}],
        }
        response = client.post("/inventory/reserve", json=payload)
        assert response.status_code == 409
        assert "Insufficient stock" in response.json()["detail"]

    def test_reserve_item_not_found(self):
        payload = {
            "order_id": "test-order-3",
            "items": [{"item_id": "nonexistent-item", "quantity": 1}],
        }
        response = client.post("/inventory/reserve", json=payload)
        assert response.status_code == 409
        assert "Insufficient stock" in response.json()["detail"]

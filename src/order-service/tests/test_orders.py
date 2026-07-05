"""Tests for the order-service API endpoints."""

from fastapi.testclient import TestClient

from main import app, orders

client = TestClient(app)


def setup_method():
    """Clear the order repo before each test for isolation."""
    orders._orders.clear()


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


class TestCreateOrder:
    def test_create_order_success(self):
        payload = {
            "customer_email": "test@example.com",
            "items": [
                {"item_id": "item-prod-101", "quantity": 1, "price": 19.99},
                {"item_id": "item-prod-102", "quantity": 2, "price": 29.99},
            ],
        }
        response = client.post("/orders", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted_and_reserved"
        assert data["total_amount"] == 79.97  # 19.99 + 2 * 29.99

    def test_create_order_invalid_email(self):
        payload = {
            "customer_email": "not-an-email",
            "items": [{"item_id": "item-prod-101", "quantity": 1, "price": 19.99}],
        }
        response = client.post("/orders", json=payload)
        assert response.status_code == 422


class TestGetOrder:
    def test_get_existing_order(self):
        create_resp = client.post(
            "/orders",
            json={
                "customer_email": "test@example.com",
                "items": [{"item_id": "item-prod-101", "quantity": 1, "price": 10.0}],
            },
        )
        order_id = create_resp.json()["order_id"]

        response = client.get(f"/orders/{order_id}")
        assert response.status_code == 200
        assert response.json()["order_id"] == order_id

    def test_get_nonexistent_order(self):
        response = client.get("/orders/nonexistent-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"


class TestListOrders:
    def test_list_orders_empty(self):
        response = client.get("/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_orders_returns_created_orders(self):
        client.post(
            "/orders",
            json={
                "customer_email": "a@b.com",
                "items": [{"item_id": "item-prod-101", "quantity": 1, "price": 10.0}],
            },
        )
        client.post(
            "/orders",
            json={
                "customer_email": "b@c.com",
                "items": [{"item_id": "item-prod-102", "quantity": 2, "price": 20.0}],
            },
        )

        response = client.get("/orders")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

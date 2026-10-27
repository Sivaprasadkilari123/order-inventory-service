from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_create_order_deducts_stock_and_totals(place_order, make_product, get_stock):
    p1 = make_product(price="49.99", qty=10)
    p2 = make_product(price="10.00", qty=5)

    r = place_order([(p1["id"], 3), (p2["id"], 2)])

    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "CONFIRMED"
    assert Decimal(body["total_amount"]) == Decimal("169.97")
    assert len(body["items"]) == 2
    assert get_stock(p1["id"]) == 7
    assert get_stock(p2["id"]) == 3


def test_failed_order_rolls_back_everything(
    client, auth_headers, place_order, make_product, get_stock
):
    p1 = make_product(qty=10)
    p2 = make_product(qty=5)

    # first line is fine, second line is impossible
    r = place_order([(p1["id"], 2), (p2["id"], 99)])

    assert r.status_code == 409
    assert get_stock(p1["id"]) == 10  # NOT deducted
    assert get_stock(p2["id"]) == 5
    assert client.get("/orders", headers=auth_headers).json() == []  # no order row


def test_duplicate_lines_are_merged_before_stock_check(place_order, make_product, get_stock):
    product = make_product(qty=7)
    r = place_order([(product["id"], 5), (product["id"], 5)])  # 10 > 7
    assert r.status_code == 409
    assert get_stock(product["id"]) == 7


def test_order_from_warehouse_without_stock_row(
    client, auth_headers, customer, make_product
):
    product = make_product()
    other = client.post("/warehouses", headers=auth_headers, json={"name": "Empty WH"}).json()
    r = client.post("/orders", headers=auth_headers, json={
        "customer_id": customer["id"],
        "items": [{"product_id": product["id"], "warehouse_id": other["id"], "quantity": 1}],
    })
    assert r.status_code == 409


def test_order_unknown_customer(place_order, make_product):
    product = make_product()
    assert place_order([(product["id"], 1)], customer_id=999999).status_code == 404


def test_order_unknown_product(place_order):
    assert place_order([(999999, 1)]).status_code == 404


@pytest.mark.parametrize("quantity", [0, -3])
def test_order_invalid_quantity(place_order, make_product, quantity):
    product = make_product()
    assert place_order([(product["id"], quantity)]).status_code == 422


def test_order_requires_at_least_one_item(client, auth_headers, customer):
    r = client.post("/orders", headers=auth_headers,
                    json={"customer_id": customer["id"], "items": []})
    assert r.status_code == 422


def test_get_missing_order(client, auth_headers):
    assert client.get("/orders/999999", headers=auth_headers).status_code == 404


def test_cancel_restores_stock(client, auth_headers, place_order, make_product, get_stock):
    product = make_product(qty=10)
    order = place_order([(product["id"], 4)]).json()
    assert get_stock(product["id"]) == 6

    r = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"
    assert get_stock(product["id"]) == 10


def test_cancel_twice_is_rejected(client, auth_headers, place_order, make_product, get_stock):
    product = make_product(qty=10)
    order = place_order([(product["id"], 4)]).json()
    client.post(f"/orders/{order['id']}/cancel", headers=auth_headers)

    r = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers)

    assert r.status_code == 409
    assert get_stock(product["id"]) == 10  # not restored a second time


def test_order_keeps_price_paid_after_price_change(client, auth_headers, place_order, make_product):
    product = make_product(price="10.00", qty=10)
    order = place_order([(product["id"], 2)]).json()

    client.patch(f"/products/{product['id']}", headers=auth_headers, json={"price": "99.00"})

    fetched = client.get(f"/orders/{order['id']}", headers=auth_headers).json()
    assert Decimal(fetched["items"][0]["unit_price"]) == Decimal("10.00")
    assert Decimal(fetched["total_amount"]) == Decimal("20.00")


def test_concurrent_orders_never_oversell(auth_headers, customer, warehouse, make_product, get_stock):
    product = make_product(price="1.00", qty=5)
    payload = {
        "customer_id": customer["id"],
        "items": [{"product_id": product["id"], "warehouse_id": warehouse["id"], "quantity": 1}],
    }

    def worker(_):
        return TestClient(app).post("/orders", headers=auth_headers, json=payload).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(worker, range(10)))

    assert codes.count(201) == 5
    assert codes.count(409) == 5
    assert get_stock(product["id"]) == 0  # never negative

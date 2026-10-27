import pytest


@pytest.mark.parametrize(
    "path", ["/customers", "/warehouses", "/products", "/inventory", "/orders"]
)
def test_endpoints_require_auth(client, path):
    assert client.get(path).status_code == 401


# ---------- customers ----------
def test_customer_create_and_get(client, auth_headers):
    r = client.post("/customers", headers=auth_headers,
                    json={"name": "Ravi", "email": "ravi@example.com", "phone": "9999999999"})
    assert r.status_code == 201
    cid = r.json()["id"]
    got = client.get(f"/customers/{cid}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["email"] == "ravi@example.com"


def test_customer_duplicate_email(client, auth_headers, customer):
    r = client.post("/customers", headers=auth_headers,
                    json={"name": "Other", "email": customer["email"]})
    assert r.status_code == 409


def test_customer_update(client, auth_headers, customer):
    r = client.patch(f"/customers/{customer['id']}", headers=auth_headers,
                     json={"phone": "8888888888"})
    assert r.status_code == 200
    assert r.json()["phone"] == "8888888888"
    assert r.json()["name"] == customer["name"]  # untouched fields stay


def test_customer_not_found(client, auth_headers):
    assert client.get("/customers/999999", headers=auth_headers).status_code == 404


def test_customer_delete(client, auth_headers, customer):
    assert client.delete(f"/customers/{customer['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/customers/{customer['id']}", headers=auth_headers).status_code == 404


# ---------- warehouses ----------
def test_warehouse_duplicate_name(client, auth_headers, warehouse):
    r = client.post("/warehouses", headers=auth_headers, json={"name": warehouse["name"]})
    assert r.status_code == 409


def test_warehouse_update(client, auth_headers, warehouse):
    r = client.patch(f"/warehouses/{warehouse['id']}", headers=auth_headers,
                     json={"location": "Mumbai"})
    assert r.status_code == 200
    assert r.json()["location"] == "Mumbai"


# ---------- products ----------
def test_product_create(client, auth_headers):
    r = client.post("/products", headers=auth_headers,
                    json={"sku": "KB-1", "name": "Keyboard", "price": "49.99"})
    assert r.status_code == 201
    assert r.json()["price"] == "49.99"


def test_product_invalid_price(client, auth_headers):
    r = client.post("/products", headers=auth_headers,
                    json={"sku": "KB-2", "name": "Keyboard", "price": "-5"})
    assert r.status_code == 422


def test_product_duplicate_sku(client, auth_headers):
    payload = {"sku": "KB-3", "name": "Keyboard", "price": "10.00"}
    client.post("/products", headers=auth_headers, json=payload)
    assert client.post("/products", headers=auth_headers, json=payload).status_code == 409


def test_product_with_stock_cannot_be_deleted(client, auth_headers, make_product):
    product = make_product()
    r = client.delete(f"/products/{product['id']}", headers=auth_headers)
    assert r.status_code == 409


# ---------- inventory ----------
def test_inventory_set_then_update(client, auth_headers, warehouse, make_product, get_stock):
    product = make_product(qty=100)
    assert get_stock(product["id"]) == 100
    client.put("/inventory", headers=auth_headers,
               json={"warehouse_id": warehouse["id"], "product_id": product["id"], "quantity": 90})
    assert get_stock(product["id"]) == 90


def test_inventory_negative_quantity_rejected(client, auth_headers, warehouse, make_product):
    product = make_product()
    r = client.put("/inventory", headers=auth_headers,
                   json={"warehouse_id": warehouse["id"], "product_id": product["id"], "quantity": -1})
    assert r.status_code == 422


def test_inventory_unknown_warehouse(client, auth_headers, make_product):
    product = make_product()
    r = client.put("/inventory", headers=auth_headers,
                   json={"warehouse_id": 999999, "product_id": product["id"], "quantity": 1})
    assert r.status_code == 404


def test_inventory_unknown_product(client, auth_headers, warehouse):
    r = client.put("/inventory", headers=auth_headers,
                   json={"warehouse_id": warehouse["id"], "product_id": 999999, "quantity": 1})
    assert r.status_code == 404


def test_inventory_filter_by_product(client, auth_headers, make_product):
    first = make_product()
    make_product()
    rows = client.get(f"/inventory?product_id={first['id']}", headers=auth_headers).json()
    assert len(rows) == 1
    assert rows[0]["product_id"] == first["id"]

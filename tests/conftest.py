import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "mysql+pymysql://app_user:app_pass123@localhost/inventory_test",
)

_url = make_url(TEST_DATABASE_URL)
# tests TRUNCATE tables, so never run against a non-test database
assert "test" in (_url.database or ""), "Refusing to run tests on a non-test database"

# must be set BEFORE the app is imported so its engine uses the test DB
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def _create_test_database():
    server_engine = create_engine(
        URL.create(
            _url.drivername,
            username=_url.username,
            password=_url.password,
            host=_url.host,
            port=_url.port,
        ),
        isolation_level="AUTOCOMMIT",
    )
    with server_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{_url.database}`"))
    server_engine.dispose()


_create_test_database()

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    creds = {"email": "tester@example.com", "password": "Secret123"}
    client.post("/auth/register", json=creds)
    r = client.post(
        "/auth/login",
        data={"username": creds["email"], "password": creds["password"]},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def customer(client, auth_headers):
    r = client.post(
        "/customers",
        headers=auth_headers,
        json={"name": "Asha", "email": "asha@example.com"},
    )
    return r.json()


@pytest.fixture
def warehouse(client, auth_headers):
    r = client.post(
        "/warehouses",
        headers=auth_headers,
        json={"name": "Main WH", "location": "Bhopal"},
    )
    return r.json()


@pytest.fixture
def make_product(client, auth_headers, warehouse):
    """Factory: creates a product and stocks it in the default warehouse."""
    counter = {"n": 0}

    def _make(price="10.00", qty=10):
        counter["n"] += 1
        sku = f"SKU-{counter['n']}"
        product = client.post(
            "/products",
            headers=auth_headers,
            json={"sku": sku, "name": sku, "price": price},
        ).json()
        client.put(
            "/inventory",
            headers=auth_headers,
            json={
                "warehouse_id": warehouse["id"],
                "product_id": product["id"],
                "quantity": qty,
            },
        )
        return product

    return _make


@pytest.fixture
def get_stock(client, auth_headers, warehouse):
    def _get(product_id):
        rows = client.get(
            f"/inventory?warehouse_id={warehouse['id']}&product_id={product_id}",
            headers=auth_headers,
        ).json()
        return rows[0]["quantity"] if rows else None

    return _get


@pytest.fixture
def place_order(client, auth_headers, customer, warehouse):
    """Helper: place_order([(product_id, qty), ...])"""

    def _place(lines, customer_id=None):
        items = [
            {"product_id": pid, "warehouse_id": warehouse["id"], "quantity": qty}
            for pid, qty in lines
        ]
        return client.post(
            "/orders",
            headers=auth_headers,
            json={"customer_id": customer_id or customer["id"], "items": items},
        )

    return _place

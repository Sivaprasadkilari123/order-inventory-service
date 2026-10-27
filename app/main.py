from fastapi import FastAPI

from app.database import Base, engine
from app import models  # noqa: F401  (registers tables)
from app.routers import (
    auth_routes, customers, inventory, orders, products, warehouses,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Order & Inventory Management Service", version="1.0.0")

app.include_router(auth_routes.router)
app.include_router(customers.router)
app.include_router(warehouses.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(orders.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

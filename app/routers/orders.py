from collections import defaultdict
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.database import get_db
from app.schemas_orders import OrderCreate, OrderOut

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(get_current_user)],
)


def _lock_stock(db: Session, warehouse_id: int, product_id: int):
    """Fetch an inventory row and lock it until the transaction ends."""
    return (
        db.query(models.Inventory)
        .filter_by(warehouse_id=warehouse_id, product_id=product_id)
        .populate_existing()
        .with_for_update()
        .first()
    )


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if not db.get(models.Customer, payload.customer_id):
        raise HTTPException(404, "Customer not found")

    # merge duplicate lines so the stock check sees the true total
    wanted = defaultdict(int)
    for line in payload.items:
        wanted[(line.warehouse_id, line.product_id)] += line.quantity

    try:
        order = models.Order(
            customer_id=payload.customer_id,
            status="CONFIRMED",
            total_amount=Decimal("0"),
        )
        db.add(order)
        total = Decimal("0")

        # consistent lock order (warehouse, product) avoids deadlocks
        for (warehouse_id, product_id), qty in sorted(wanted.items()):
            product = db.get(models.Product, product_id)
            if not product:
                raise HTTPException(404, f"Product {product_id} not found")

            stock = _lock_stock(db, warehouse_id, product_id)
            if stock is None or stock.quantity < qty:
                available = stock.quantity if stock else 0
                raise HTTPException(
                    409,
                    f"Insufficient stock for product {product_id} in warehouse "
                    f"{warehouse_id}: requested {qty}, available {available}",
                )

            stock.quantity -= qty
            order.items.append(
                models.OrderItem(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=qty,
                    unit_price=product.price,
                )
            )
            total += product.price * qty

        order.total_amount = total
        db.commit()  # order + items + all stock deductions land together
    except Exception:
        db.rollback()  # ...or none of them do
        raise

    db.refresh(order)
    return order


@router.get("", response_model=List[OrderOut])
def list_orders(
    customer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(models.Order)
    if customer_id is not None:
        query = query.filter(models.Order.customer_id == customer_id)
    return query.order_by(models.Order.id).offset(skip).limit(limit).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    try:
        order = (
            db.query(models.Order)
            .filter(models.Order.id == order_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not order:
            raise HTTPException(404, "Order not found")
        if order.status == "CANCELLED":
            raise HTTPException(409, "Order already cancelled")

        for item in sorted(order.items, key=lambda i: (i.warehouse_id, i.product_id)):
            stock = _lock_stock(db, item.warehouse_id, item.product_id)
            if stock is None:
                stock = models.Inventory(
                    warehouse_id=item.warehouse_id,
                    product_id=item.product_id,
                    quantity=0,
                )
                db.add(stock)
            stock.quantity += item.quantity

        order.status = "CANCELLED"
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order

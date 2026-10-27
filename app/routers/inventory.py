from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(get_current_user)],
)


@router.put("", response_model=schemas.InventoryOut)
def set_stock(payload: schemas.InventorySet, db: Session = Depends(get_db)):
    """Set the stock level of a product in a warehouse (creates the row if missing)."""
    if not db.get(models.Warehouse, payload.warehouse_id):
        raise HTTPException(404, "Warehouse not found")
    if not db.get(models.Product, payload.product_id):
        raise HTTPException(404, "Product not found")

    row = (
        db.query(models.Inventory)
        .filter_by(warehouse_id=payload.warehouse_id, product_id=payload.product_id)
        .first()
    )
    if row:
        row.quantity = payload.quantity
    else:
        row = models.Inventory(**payload.model_dump())
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=List[schemas.InventoryOut])
def list_inventory(
    warehouse_id: Optional[int] = None,
    product_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(models.Inventory)
    if warehouse_id is not None:
        query = query.filter(models.Inventory.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.filter(models.Inventory.product_id == product_id)
    return query.order_by(models.Inventory.id).offset(skip).limit(limit).all()

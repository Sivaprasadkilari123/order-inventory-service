from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/warehouses",
    tags=["warehouses"],
    dependencies=[Depends(get_current_user)],
)


def _get_or_404(db: Session, warehouse_id: int) -> models.Warehouse:
    warehouse = db.get(models.Warehouse, warehouse_id)
    if not warehouse:
        raise HTTPException(404, "Warehouse not found")
    return warehouse


@router.post("", response_model=schemas.WarehouseOut, status_code=201)
def create_warehouse(payload: schemas.WarehouseCreate, db: Session = Depends(get_db)):
    warehouse = models.Warehouse(**payload.model_dump())
    db.add(warehouse)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Warehouse name already exists")
    db.refresh(warehouse)
    return warehouse


@router.get("", response_model=List[schemas.WarehouseOut])
def list_warehouses(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.Warehouse).order_by(models.Warehouse.id).offset(skip).limit(limit).all()


@router.get("/{warehouse_id}", response_model=schemas.WarehouseOut)
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, warehouse_id)


@router.patch("/{warehouse_id}", response_model=schemas.WarehouseOut)
def update_warehouse(warehouse_id: int, payload: schemas.WarehouseUpdate, db: Session = Depends(get_db)):
    warehouse = _get_or_404(db, warehouse_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(warehouse, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Warehouse name already exists")
    db.refresh(warehouse)
    return warehouse


@router.delete("/{warehouse_id}", status_code=204)
def delete_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = _get_or_404(db, warehouse_id)
    db.delete(warehouse)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Warehouse still has inventory or orders")

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Customers ----------
class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=255)


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=255)


class CustomerOut(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


# ---------- Warehouses ----------
class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: Optional[str] = Field(default=None, max_length=255)


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    location: Optional[str] = Field(default=None, max_length=255)


class WarehouseOut(WarehouseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


# ---------- Products ----------
class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)


class ProductOut(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


# ---------- Inventory ----------
class InventorySet(BaseModel):
    warehouse_id: int
    product_id: int
    quantity: int = Field(ge=0)


class InventoryOut(InventorySet):
    model_config = ConfigDict(from_attributes=True)

    id: int

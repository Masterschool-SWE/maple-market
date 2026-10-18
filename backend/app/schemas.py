"""Request/response schemas (separate from the DB tables in models.py)."""
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class UserCreate(SQLModel):
    username: str
    password: str


class UserRead(SQLModel):
    id: int
    username: str
    created_at: datetime


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class ProductRead(SQLModel):
    id: int
    name: str
    sku: str
    category: str
    price_cents: int
    description: str


class OrderCreate(SQLModel):
    product_id: int
    quantity: int = 1


class OrderItemRead(SQLModel):
    product_name: str
    quantity: int
    unit_price_cents: int


class OrderRead(SQLModel):
    id: int
    status: str
    total_cents: int
    created_at: datetime
    delivered_at: Optional[datetime] = None
    items: list[OrderItemRead] = []


class AgentInvokeRequest(SQLModel):
    """The contract for talking to the support assistant."""
    message: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    reasoning_effort: Optional[str] = None


class AgentInvokeResponse(SQLModel):
    reply: str

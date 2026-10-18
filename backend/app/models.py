"""SQLModel database tables — shop catalog, orders, and support threads."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=_utcnow)

    orders: List["Order"] = Relationship(back_populates="user")
    threads: List["SupportThread"] = Relationship(back_populates="user")


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    sku: str = Field(index=True, unique=True)
    category: str = Field(default="General", index=True)
    price_cents: int = 0
    description: str = ""

    items: List["OrderItem"] = Relationship(back_populates="product")


class Order(SQLModel, table=True):
    __tablename__ = "shop_order"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    status: str = "placed"  # placed | processing | shipped | delivered | cancelled
    total_cents: int = 0
    delivered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)

    user: Optional[User] = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="shop_order.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    quantity: int = 1
    unit_price_cents: int = 0

    order: Optional[Order] = Relationship(back_populates="items")
    product: Optional[Product] = Relationship(back_populates="items")


class SupportThread(SQLModel, table=True):
    """One conversational thread per customer. ``thread_id`` drives the checkpointer."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    thread_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow)

    user: Optional[User] = Relationship(back_populates="threads")

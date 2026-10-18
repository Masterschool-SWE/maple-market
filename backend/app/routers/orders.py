"""Order routes (scoped to the logged-in customer)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..auth import get_current_user
from ..database import get_session
from ..models import Order, OrderItem, Product, User
from ..schemas import OrderCreate, OrderItemRead, OrderRead, ProductRead

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_read(order: Order) -> OrderRead:
    return OrderRead(
        id=order.id,
        status=order.status,
        total_cents=order.total_cents,
        created_at=order.created_at,
        delivered_at=order.delivered_at,
        items=[
            OrderItemRead(
                product_name=item.product.name if item.product else "?",
                quantity=item.quantity,
                unit_price_cents=item.unit_price_cents,
            )
            for item in order.items
        ],
    )


@router.get("/products", response_model=list[ProductRead])
def list_products(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(select(Product).order_by(Product.category, Product.name)).all()


@router.post("", response_model=OrderRead, status_code=201)
def create_order(
    data: OrderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if data.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    product = session.get(Product, data.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    order = Order(
        user_id=current_user.id,
        status="placed",
        total_cents=product.price_cents * data.quantity,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    session.add(OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=data.quantity,
        unit_price_cents=product.price_cents,
    ))
    session.commit()
    return get_order(order.id, session, current_user)


@router.get("", response_model=list[OrderRead])
def list_orders(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    orders = session.exec(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    ).all()
    return [_to_read(o) for o in orders]


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    order = session.exec(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    ).first()
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return _to_read(order)

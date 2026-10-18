"""Seed catalog, two customers, and orders with mixed statuses.

Demo:     username ``demo``  /  password ``demo1234``
Other:    username ``other`` /  password ``other1234``
"""
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from .auth import hash_password
from .models import Order, OrderItem, Product, User

PRODUCTS = [
    {"name": "AeroBlend 3000", "sku": "BLND-3000", "category": "Kitchen",
     "price_cents": 8900, "description": "Countertop blender. Glass jug, 600W."},
    {"name": "DripKit coffee maker", "sku": "COF-DRIP", "category": "Kitchen",
     "price_cents": 6500, "description": "Pour-over style coffee maker, 1.2L."},
    {"name": "Stone mug", "sku": "MUG-STN", "category": "Kitchen",
     "price_cents": 1200, "description": "Ceramic mug, 350ml."},
    {"name": "Amber maple syrup", "sku": "EAR-QUIET", "category": "Pantry",
     "price_cents": 1400, "description": "Grade A amber syrup, 250ml glass bottle."},
    {"name": "Forest breakfast tea", "sku": "SPK-DESK", "category": "Pantry",
     "price_cents": 900, "description": "Loose-leaf black tea with maple and spice, 80g."},
    {"name": "Canvas market tote", "sku": "APP-TEE-M", "category": "Home",
     "price_cents": 1800, "description": "Heavy canvas tote, one size."},
    {"name": "Linen apron", "sku": "APP-HOOD", "category": "Kitchen",
     "price_cents": 3200, "description": "Natural linen apron with a front pocket."},
    {"name": "Beeswax pillar candle", "sku": "HOME-LAMP", "category": "Home",
     "price_cents": 1600, "description": "Unscented beeswax candle, 12cm."},
]


def _days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def seed_initial_data(engine) -> None:
    with Session(engine) as session:
        for row in PRODUCTS:
            existing = session.exec(select(Product).where(Product.sku == row["sku"])).first()
            if existing is None:
                session.add(Product(**row))
            else:
                existing.name = row["name"]
                existing.category = row["category"]
                existing.price_cents = row["price_cents"]
                existing.description = row["description"]
                session.add(existing)
        session.commit()

        if session.exec(select(User).where(User.username == "demo")).first() is not None:
            return

        def product(sku: str) -> Product:
            return session.exec(select(Product).where(Product.sku == sku)).one()

        demo = User(username="demo", hashed_password=hash_password("demo1234"))
        other = User(username="other", hashed_password=hash_password("other1234"))
        session.add_all([demo, other])
        session.commit()
        session.refresh(demo)
        session.refresh(other)

        blender = product("BLND-3000")
        buds = product("EAR-QUIET")
        coffee = product("COF-DRIP")
        tee = product("APP-TEE-M")

        def add_order(*, user: User, status: str, days: int, lines: list[tuple[Product, int]], delivered_days: int | None = None) -> None:
            total = sum(p.price_cents * qty for p, qty in lines)
            order = Order(
                user_id=user.id,
                status=status,
                total_cents=total,
                created_at=_days_ago(days),
                delivered_at=_days_ago(delivered_days) if delivered_days is not None else None,
            )
            session.add(order)
            session.commit()
            session.refresh(order)
            session.add_all(
                OrderItem(order_id=order.id, product_id=p.id, quantity=qty, unit_price_cents=p.price_cents)
                for p, qty in lines
            )
            session.commit()

        add_order(user=demo, status="delivered", days=40, delivered_days=35, lines=[(blender, 1)])
        add_order(user=demo, status="delivered", days=10, delivered_days=5, lines=[(buds, 1)])
        add_order(user=demo, status="shipped", days=2, lines=[(coffee, 1)])
        add_order(user=demo, status="placed", days=0, lines=[(tee, 2)])
        add_order(user=other, status="placed", days=1, lines=[(buds, 1)])

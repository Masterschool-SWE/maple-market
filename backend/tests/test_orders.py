"""Order listing and cancel_order write-tool tests."""
from langchain_core.runnables import RunnableConfig

from app.agent.tools import cancel_order, list_my_orders
from app.models import Order


def _login(client, username, password):
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_demo_sees_own_orders(client):
    headers = _login(client, "demo", "demo1234")
    r = client.get("/orders", headers=headers)
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) == 4
    statuses = {o["status"] for o in orders}
    assert statuses == {"delivered", "shipped", "placed"}


def test_place_order_from_catalog(client):
    headers = _login(client, "demo", "demo1234")
    products = client.get("/orders/products", headers=headers)
    assert products.status_code == 200
    catalog = products.json()
    assert {p["category"] for p in catalog} >= {"Kitchen", "Pantry", "Home"}
    mug = next(p for p in catalog if p["sku"] == "MUG-STN")
    before = client.get("/orders", headers=headers).json()
    r = client.post("/orders", json={"product_id": mug["id"], "quantity": 2}, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "placed"
    assert body["total_cents"] == mug["price_cents"] * 2
    assert body["items"][0]["product_name"] == "Stone mug"
    after = client.get("/orders", headers=headers).json()
    assert len(after) == len(before) + 1


def test_list_my_orders_is_live_sql(client):
    headers = _login(client, "demo", "demo1234")
    products = client.get("/orders/products", headers=headers).json()
    mug = next(p for p in products if p["sku"] == "MUG-STN")
    client.post("/orders", json={"product_id": mug["id"], "quantity": 1}, headers=headers)

    from sqlmodel import Session, select

    from app.database import engine

    with Session(engine) as session:
        demo_id = session.exec(select(Order).where(Order.status == "delivered")).first().user_id
        n = len(session.exec(select(Order).where(Order.user_id == demo_id)).all())

    text = list_my_orders.invoke({}, config=RunnableConfig(configurable={"user_id": demo_id}))
    assert f"{n} order(s):" in text
    assert "delivered" in text and "shipped" in text and "placed" in text


def test_demo_cannot_fetch_others_order(client):
    other = _login(client, "other", "other1234")
    theirs = client.get("/orders", headers=other).json()
    assert len(theirs) == 1
    other_id = theirs[0]["id"]

    demo = _login(client, "demo", "demo1234")
    r = client.get(f"/orders/{other_id}", headers=demo)
    assert r.status_code == 404


def test_cancel_order_writes_placed_only(client):
    from sqlmodel import Session, select

    from app.database import engine

    with Session(engine) as session:
        demo_id = session.exec(select(Order).where(Order.status == "placed")).first().user_id
        placed = session.exec(select(Order).where(Order.user_id == demo_id, Order.status == "placed")).one()
        shipped = session.exec(select(Order).where(Order.user_id == demo_id, Order.status == "shipped")).one()
        placed_id, shipped_id = placed.id, shipped.id

    cfg = RunnableConfig(configurable={"user_id": demo_id})
    assert "Cancelled" in cancel_order.invoke({"order_id": placed_id}, config=cfg)
    assert "Cannot cancel" in cancel_order.invoke({"order_id": shipped_id}, config=cfg)

    with Session(engine) as session:
        assert session.get(Order, placed_id).status == "cancelled"
        assert session.get(Order, shipped_id).status == "shipped"

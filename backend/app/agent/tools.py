"""Tools the assistant can call.

- ``search_policies`` — RAG over cancellations, returns, delivery.
- ``ask_archivist`` — SQL sub-agent over the shop database.
- ``cancel_order`` — the only write tool; updates order status in SQLite.
"""
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..database import engine
from ..models import Order, OrderItem
from .archivist import build_archivist
from .rag.retriever import get_retriever


@tool
def search_policies(query: str) -> str:
    """Search shop policies: cancellations, returns, refunds, and delivery.

    Use this before stating a rule (return window, when cancel is allowed, delivery times).
    """
    try:
        docs = get_retriever().invoke(query)
    except Exception as exc:
        return f"Policy search failed: {exc}"
    if not docs:
        return "No matching policy passages. (Have the policies been ingested?)"
    return "\n\n---\n\n".join(
        f"[source: {d.metadata.get('source', '?')}]\n{d.page_content}" for d in docs
    )


@tool
def list_my_orders(config: RunnableConfig) -> str:
    """List every order for the logged-in customer: id, status, total, items.

    Use this for any question about how many orders they have, what they bought,
    or an order's status. The shop UI can add orders that are not in the chat history.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "Rejected: not logged in."
    with Session(engine) as session:
        orders = session.exec(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.id)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
        ).all()
    if not orders:
        return "This customer has no orders."
    lines = [f"{len(orders)} order(s):"]
    for order in orders:
        items = ", ".join(
            f"{item.quantity}× {item.product.name if item.product else '?'}"
            for item in order.items
        )
        lines.append(
            f"#{order.id} · {order.status} · €{order.total_cents / 100:.2f} · {items}"
        )
    return "\n".join(lines)


@tool
def ask_archivist(question: str, config: RunnableConfig) -> str:
    """Look up the customer's orders, items, and statuses in the shop database.

    Always include the logged-in customer user_id from the system prompt in your question.
    """
    try:
        user_id = (config or {}).get("configurable", {}).get("user_id")
        if user_id is not None:
            question = f"{question}\n(Logged-in customer user_id={user_id}. Filter to their rows.)"
        archivist = build_archivist()
        child_config = {}
        if config and config.get("callbacks"):
            child_config["callbacks"] = config["callbacks"]
        result = archivist.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config=child_config,
        )
        content = result["messages"][-1].content
        return content if isinstance(content, str) else str(content)
    except Exception as exc:
        return f"The Archivist could not answer: {exc}"


@tool
def cancel_order(order_id: int, config: RunnableConfig) -> str:
    """Cancel an order in the database. Only works for the logged-in customer's
    orders that are still `placed` or `processing`. Saying so in chat is not enough.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "Rejected: not logged in."
    with Session(engine) as session:
        order = session.get(Order, order_id)
        if not order or order.user_id != user_id:
            return "Order not found."
        if order.status not in ("placed", "processing"):
            return (
                f"Cannot cancel: order {order_id} is '{order.status}'. "
                "Only placed or processing orders can be cancelled."
            )
        order.status = "cancelled"
        session.add(order)
        session.commit()
        return f"Cancelled order {order_id}."


def get_keeper_tools() -> list:
    return [search_policies, list_my_orders, ask_archivist, cancel_order]

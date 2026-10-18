"""The Archivist — a SQL-expert sub-agent.

Read-only ``execute_sql``. The assistant calls this via ``ask_archivist``.
"""
import re
import sqlite3

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from ..config import ARCHIVIST_MODEL, SQLITE_PATH, openai_client_kwargs

SCHEMA = """\
shop_order(id, user_id, status, total_cents, delivered_at, created_at)
  -- status: placed|processing|shipped|delivered|cancelled
orderitem(id, order_id, product_id, quantity, unit_price_cents)
product(id, name, sku, category, price_cents, description)
supportthread(id, user_id, thread_id, created_at)
"""

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b", re.IGNORECASE
)


@tool
def execute_sql(query: str) -> str:
    """Run a single read-only SQL SELECT against the shop database and return the rows as text."""
    q = query.strip().rstrip(";").strip()
    if not q.lower().startswith("select"):
        return "Rejected: only SELECT queries are allowed."
    if ";" in q:
        return "Rejected: only a single statement is allowed."
    if _FORBIDDEN.search(q):
        return "Rejected: query contains a forbidden (write) keyword."

    try:
        conn = sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True)
        cur = conn.execute(q)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(50)
        conn.close()
    except Exception as exc:
        return f"SQL error: {exc}"

    if not rows:
        return "No rows."
    header = " | ".join(cols)
    body = "\n".join(" | ".join(str(v) for v in row) for row in rows)
    return f"{header}\n{body}"


ARCHIVIST_SYSTEM_PROMPT = f"""\
You are the Archivist, a SQL expert for the shop database (SQLite).
Answer by writing and running SQL with execute_sql. Rules:
- SELECT only. One statement at a time.
- Prefer filtering orders by the customer user_id given in the question.
- Inspect the rows, then answer in one or two plain sentences.
- If a query errors, fix the SQL and try again.

The schema:
{SCHEMA}
"""


def build_archivist(model: str | None = None):
    llm = init_chat_model(model or ARCHIVIST_MODEL, **openai_client_kwargs())
    return create_agent(llm, tools=[execute_sql], system_prompt=ARCHIVIST_SYSTEM_PROMPT)

"""Maple Market — login, orders, and customer-support chat."""
import os
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Maple Market Support", page_icon="🍁", layout="centered")

ss = st.session_state
ss.setdefault("token", None)
ss.setdefault("username", None)
ss.setdefault("messages", [])
ss.setdefault("model", os.getenv("KEEPER_MODEL", "openai:gpt-4o-mini"))
ss.setdefault("temperature", float(os.getenv("KEEPER_TEMPERATURE", "0.3")))
ss.setdefault("orders", None)
ss.setdefault("catalog", None)


def api(method: str, path: str, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    if ss.token:
        headers["Authorization"] = f"Bearer {ss.token}"
    timeout = float(os.getenv("BACKEND_TIMEOUT", "180"))
    return httpx.request(method, f"{BACKEND_URL}{path}", headers=headers, timeout=timeout, **kwargs)


def money(cents: int) -> str:
    return f"€{cents / 100:.2f}"


def logout():
    ss.token = ss.username = None
    ss.messages = []
    ss.orders = None
    ss.catalog = None


def load_orders(*, force: bool = False) -> list:
    if force or ss.orders is None:
        r = api("GET", "/orders")
        ss.orders = r.json() if r.status_code == 200 else []
    return ss.orders


def load_catalog() -> list:
    if ss.catalog is None:
        r = api("GET", "/orders/products")
        ss.catalog = r.json() if r.status_code == 200 else []
    return ss.catalog


def auth_view():
    st.title("🍁 Maple Market")
    st.caption("Customer support")
    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        st.caption("Demo → `demo` / `demo1234` · second customer → `other` / `other1234`")
        if st.button("Log in", key="login_btn", type="primary"):
            r = api("POST", "/auth/login", data={"username": u, "password": p})
            if r.status_code == 200:
                ss.token = r.json()["access_token"]
                ss.username = u
                ss.messages = []
                ss.orders = None
                ss.catalog = None
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    with tab_register:
        u = st.text_input("Choose a username", key="reg_u")
        p = st.text_input("Choose a password", type="password", key="reg_p")
        if st.button("Create account", key="reg_btn"):
            r = api("POST", "/auth/register", json={"username": u, "password": p})
            if r.status_code == 201:
                st.success("Account created — now log in.")
            else:
                st.error(r.json().get("detail", "Could not register."))


def sidebar():
    with st.sidebar:
        st.header(f"👤 {ss.username}")
        if st.button("Log out"):
            logout()
            st.rerun()

        st.divider()
        st.caption("Your orders")
        for order in load_orders():
            st.write(f"#{order['id']} · {order['status']} · {money(order['total_cents'])}")

        catalog = load_catalog()
        with st.expander("➕ Place an order"):
            if not catalog:
                st.info("No products in the catalog.")
            else:
                with st.form("place_order"):
                    labels = {
                        f"{p['category']} · {p['name']} · {money(p['price_cents'])}": p
                        for p in sorted(catalog, key=lambda p: (p["category"], p["name"]))
                    }
                    chosen = st.selectbox("Product", list(labels.keys()))
                    qty = st.number_input("Quantity", min_value=1, max_value=9, value=1)
                    submitted = st.form_submit_button("Place order")
                if submitted:
                    product = labels[chosen]
                    r = api("POST", "/orders", json={"product_id": product["id"], "quantity": int(qty)})
                    if r.status_code == 201:
                        load_orders(force=True)
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Could not place order."))

        with st.expander("⚙️ Assistant settings"):
            st.text_input("Model", key="model")
            st.slider("Temperature", 0.0, 1.5, step=0.1, key="temperature")


def chat_view():
    st.title("🍁 Maple Market")
    st.caption("Customer support — orders, delivery, returns, and cancellations.")

    for msg in ss.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Message customer support..."):
        ss.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Looking that up..."):
                r = api("POST", "/agent/invoke", json={
                    "message": prompt, "model": ss.model, "temperature": ss.temperature,
                })
            if r.status_code == 200:
                reply = r.json()["reply"]
            else:
                detail = r.json().get("detail", "an error occurred")
                reply = f"*({detail})*"
            st.markdown(reply)
        ss.messages.append({"role": "assistant", "content": reply})


if ss.token is None:
    auth_view()
else:
    sidebar()
    chat_view()

"""FastAPI application entrypoint for Maple Market."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import create_db_and_tables, engine
from .routers import agent, auth, orders, users
from .seed import seed_initial_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_initial_data(engine)
    yield


app = FastAPI(title="Maple Market API", version="0.3.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(agent.router)


@app.get("/", tags=["meta"])
def root():
    return {"app": "Maple Market", "docs": "/docs"}

"""Short-term memory for the Keeper — a LangGraph SQLite checkpointer ("the Chronicle").

A checkpointer persists the graph state (the message history) per ``thread_id``. We use one
thread per hero's adventure, so each hero remembers its own conversation across turns.
"""
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from ..config import CHECKPOINT_DB_PATH

Path(CHECKPOINT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# check_same_thread=False because FastAPI may touch this connection from worker threads.
_conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)

checkpointer = SqliteSaver(_conn)
checkpointer.setup()  # creates the checkpoint tables if they don't exist yet

"""Application configuration, read from environment variables (.env supported)."""
import os

from dotenv import load_dotenv

load_dotenv()  # load variables from a local .env file if present

# --- Auth ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-to-a-long-random-string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/shopassistant.db")

# --- The assistant (agent) ---
# Model string understood by init_chat_model, e.g. "openai:gpt-4o-mini".
KEEPER_MODEL = os.getenv("KEEPER_MODEL", "openai:gpt-4o-mini")
KEEPER_TEMPERATURE = float(os.getenv("KEEPER_TEMPERATURE", "0.3"))

CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "./data/checkpoints.db")

MAX_THREAD_MESSAGES = int(os.getenv("MAX_THREAD_MESSAGES", "20"))
MAX_TOOL_RESULT_CHARS = int(os.getenv("MAX_TOOL_RESULT_CHARS", "1500"))

# --- The Archivist (SQL sub-agent) ---
ARCHIVIST_MODEL = os.getenv("ARCHIVIST_MODEL", KEEPER_MODEL)

SQLITE_PATH = DATABASE_URL[len("sqlite:///"):] if DATABASE_URL.startswith("sqlite:///") else DATABASE_URL

# Tables the Archivist may read. Note `user` is intentionally excluded (password hashes).
ARCHIVIST_TABLES = ["shop_order", "orderitem", "product", "supportthread"]

# --- RAG (shop policies) ---
WORLDBOOK_DIR = os.getenv("WORLDBOOK_DIR", "./assets/policies")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./data/chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "policies")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai:text-embedding-3-small")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "basic")


def openai_client_kwargs() -> dict:
    """Optional SSL bypass for school/corporate networks. Local only."""
    if os.getenv("SSL_VERIFY", "true").strip().lower() not in {"0", "false", "no", "off"}:
        return {}
    try:
        from openai import DefaultHttpxClient

        return {"http_client": DefaultHttpxClient(verify=False)}
    except ImportError:
        import httpx

        return {"http_client": httpx.Client(verify=False)}

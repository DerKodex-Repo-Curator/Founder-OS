"""DB and vector-store self-repair."""
import logging
import os

logger = logging.getLogger(__name__)


def check_sqlite() -> dict:
    try:
        from memory.sql_store import get_conn
        conn = get_conn()
        conn.execute("SELECT 1")
        conn.close()
        return {"ok": True, "component": "sqlite"}
    except Exception as e:
        return {"ok": False, "component": "sqlite", "error": str(e)[:200]}


def repair_sqlite() -> dict:
    r = check_sqlite()
    if r["ok"]:
        return r
    try:
        from agent.store import init_agent_db
        init_agent_db()
        return {"ok": True, "repaired": True, "component": "sqlite"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def check_vector_store() -> dict:
    from config import config
    backend = getattr(config, "vector_backend", "chroma")
    try:
        if backend == "qdrant":
            from config import config as cfg
            if not cfg.qdrant_url:
                return {"ok": False, "component": "qdrant", "error": "QDRANT_URL not set"}
            from qdrant_client import QdrantClient
            client = QdrantClient(url=cfg.qdrant_url, api_key=cfg.qdrant_api_key or None)
            client.get_collections()
            return {"ok": True, "component": "qdrant"}
        else:
            chroma_path = "./data/chroma"
            if not os.path.isdir(chroma_path):
                os.makedirs(chroma_path, exist_ok=True)
            return {"ok": True, "component": "chroma", "path": chroma_path}
    except Exception as e:
        return {"ok": False, "component": backend, "error": str(e)[:200]}


def repair_vector_store() -> dict:
    r = check_vector_store()
    if r["ok"]:
        return r
    try:
        chroma_path = "./data/chroma"
        os.makedirs(chroma_path, exist_ok=True)
        return {"ok": True, "repaired": True, "component": "vector", "path": chroma_path}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def full_storage_health() -> dict:
    return {
        "sqlite": check_sqlite(),
        "vector": check_vector_store(),
    }

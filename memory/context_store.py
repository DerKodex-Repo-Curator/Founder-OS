"""Context Spaces persistence — named knowledge buckets with assets and aliases."""
import os
import sqlite3
from datetime import datetime
from typing import Optional

from memory.sql_store import get_conn

CONTEXT_DATA_DIR = "./data/context"
os.makedirs(CONTEXT_DATA_DIR, exist_ok=True)

ASSET_KINDS = {"file", "audio", "video", "image", "link", "note"}
ASSET_STATUSES = {"pending", "processing", "ready", "failed"}


def init_context_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS context_spaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS context_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            space_id INTEGER NOT NULL REFERENCES context_spaces(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            title TEXT,
            source_path TEXT,
            url TEXT,
            mime TEXT,
            status TEXT DEFAULT 'pending',
            text_chars INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0,
            error TEXT,
            extracted_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS context_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            space_id INTEGER NOT NULL REFERENCES context_spaces(id) ON DELETE CASCADE,
            alias TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(space_id, alias)
        );

        CREATE INDEX IF NOT EXISTS idx_context_assets_space ON context_assets(space_id);
        CREATE INDEX IF NOT EXISTS idx_context_aliases_space ON context_aliases(space_id);
        """
    )
    conn.commit()
    conn.close()


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(row) -> dict:
    return dict(row) if row else {}


# ── Spaces ────────────────────────────────────────────────────────────────────

def create_space(name: str, description: str = "") -> dict:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO context_spaces (name, description) VALUES (?, ?)",
            (name.strip(), (description or "").strip()),
        )
        conn.commit()
        space_id = cur.lastrowid
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"Space '{name}' already exists") from e
    row = conn.execute("SELECT * FROM context_spaces WHERE id = ?", (space_id,)).fetchone()
    conn.close()
    os.makedirs(os.path.join(CONTEXT_DATA_DIR, str(space_id)), exist_ok=True)
    return _row_to_dict(row)


def list_spaces() -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT s.*,
               (SELECT COUNT(*) FROM context_assets a WHERE a.space_id = s.id) AS asset_count,
               (SELECT COUNT(*) FROM context_aliases al WHERE al.space_id = s.id) AS alias_count
        FROM context_spaces s
        ORDER BY s.updated_at DESC, s.id DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_space(space_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM context_spaces WHERE id = ?", (space_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def get_space_by_name(name: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM context_spaces WHERE lower(name) = lower(?)",
        (name.strip(),),
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def update_space(space_id: int, name: str = None, description: str = None) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM context_spaces WHERE id = ?", (space_id,)).fetchone()
    if not row:
        conn.close()
        return None
    new_name = name.strip() if name is not None else row["name"]
    new_desc = description if description is not None else row["description"]
    try:
        conn.execute(
            "UPDATE context_spaces SET name = ?, description = ?, updated_at = ? WHERE id = ?",
            (new_name, new_desc, _now(), space_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"Space '{new_name}' already exists") from e
    updated = conn.execute("SELECT * FROM context_spaces WHERE id = ?", (space_id,)).fetchone()
    conn.close()
    return _row_to_dict(updated)


def delete_space(space_id: int) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT id FROM context_spaces WHERE id = ?", (space_id,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM context_spaces WHERE id = ?", (space_id,))
    conn.commit()
    conn.close()
    space_dir = os.path.join(CONTEXT_DATA_DIR, str(space_id))
    if os.path.isdir(space_dir):
        import shutil
        try:
            shutil.rmtree(space_dir)
        except OSError:
            pass
    return True


# ── Aliases ───────────────────────────────────────────────────────────────────

def list_aliases(space_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM context_aliases WHERE space_id = ? ORDER BY alias",
        (space_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_alias(space_id: int, alias: str) -> dict:
    alias = alias.strip()
    if not alias:
        raise ValueError("Alias cannot be empty")
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO context_aliases (space_id, alias) VALUES (?, ?)",
            (space_id, alias),
        )
        conn.commit()
        alias_id = cur.lastrowid
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"Alias '{alias}' already exists for this space") from e
    row = conn.execute("SELECT * FROM context_aliases WHERE id = ?", (alias_id,)).fetchone()
    conn.commit()
    conn.execute(
        "UPDATE context_spaces SET updated_at = ? WHERE id = ?",
        (_now(), space_id),
    )
    conn.commit()
    conn.close()
    return _row_to_dict(row)


def delete_alias(alias_id: int) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT space_id FROM context_aliases WHERE id = ?", (alias_id,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM context_aliases WHERE id = ?", (alias_id,))
    conn.commit()
    conn.execute(
        "UPDATE context_spaces SET updated_at = ? WHERE id = ?",
        (_now(), row["space_id"]),
    )
    conn.commit()
    conn.close()
    return True


def all_trigger_phrases() -> list:
    """Return [{space_id, space_name, phrase}] for names + aliases."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT s.id AS space_id, s.name AS space_name, s.name AS phrase FROM context_spaces s
        UNION ALL
        SELECT s.id AS space_id, s.name AS space_name, a.alias AS phrase
        FROM context_aliases a
        JOIN context_spaces s ON s.id = a.space_id
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Assets ────────────────────────────────────────────────────────────────────

def create_asset(
    space_id: int,
    kind: str,
    title: str = "",
    source_path: str = "",
    url: str = "",
    mime: str = "",
    status: str = "pending",
    extracted_text: str = "",
) -> dict:
    if kind not in ASSET_KINDS:
        raise ValueError(f"Invalid asset kind: {kind}")
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO context_assets
            (space_id, kind, title, source_path, url, mime, status, extracted_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            space_id,
            kind,
            (title or "").strip(),
            source_path or "",
            url or "",
            mime or "",
            status,
            extracted_text or "",
        ),
    )
    conn.commit()
    asset_id = cur.lastrowid
    conn.execute(
        "UPDATE context_spaces SET updated_at = ? WHERE id = ?",
        (_now(), space_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM context_assets WHERE id = ?", (asset_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_assets(space_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM context_assets WHERE space_id = ? ORDER BY id DESC",
        (space_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_asset(asset_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM context_assets WHERE id = ?", (asset_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def update_asset(asset_id: int, **fields) -> Optional[dict]:
    allowed = {
        "kind", "title", "source_path", "url", "mime", "status",
        "text_chars", "chunk_count", "error", "extracted_text",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_asset(asset_id)
    updates["updated_at"] = _now()
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [asset_id]
    conn = get_conn()
    row = conn.execute("SELECT space_id FROM context_assets WHERE id = ?", (asset_id,)).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute(f"UPDATE context_assets SET {sets} WHERE id = ?", vals)
    conn.execute(
        "UPDATE context_spaces SET updated_at = ? WHERE id = ?",
        (_now(), row["space_id"]),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM context_assets WHERE id = ?", (asset_id,)).fetchone()
    conn.close()
    return _row_to_dict(updated)


def delete_asset(asset_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM context_assets WHERE id = ?", (asset_id,)).fetchone()
    if not row:
        conn.close()
        return None
    asset = dict(row)
    conn.execute("DELETE FROM context_assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()
    if asset.get("source_path") and os.path.isfile(asset["source_path"]):
        try:
            os.remove(asset["source_path"])
        except OSError:
            pass
    return asset


def asset_storage_path(space_id: int, asset_id: int, filename: str) -> str:
    space_dir = os.path.join(CONTEXT_DATA_DIR, str(space_id))
    os.makedirs(space_dir, exist_ok=True)
    safe = os.path.basename(filename).replace(" ", "_")
    return os.path.join(space_dir, f"{asset_id}__{safe}")


init_context_db()

"""Agent persistence layer.

Adds the self-evolving agent's own tables to the existing SQLite database
(`data/founder_os.db`): reminders, goals, lessons, skills, approvals, and a
full action audit log. Tables are created idempotently on import.
"""
import json
import sqlite3
from datetime import datetime
from typing import Optional

from memory.sql_store import get_conn  # reuse the same DB connection helper


def init_agent_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            due_at TIMESTAMP NOT NULL,
            repeat TEXT,                       -- null | 'daily' | 'weekly' | 'monthly'
            status TEXT DEFAULT 'pending',     -- pending | done | cancelled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            detail TEXT,
            status TEXT DEFAULT 'active',      -- active | done | paused | dropped
            priority INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            situation TEXT,
            lesson TEXT NOT NULL,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            when_to_use TEXT,
            steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT,
            tool_name TEXT NOT NULL,
            args_json TEXT,
            summary TEXT,
            status TEXT DEFAULT 'pending',     -- pending | approved | rejected | executed | failed
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            decided_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT,                        -- 'agent' | 'user' | 'heartbeat'
            tool_name TEXT,
            args_json TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            rationale TEXT,
            status TEXT DEFAULT 'open',        -- open | done | abandoned
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER REFERENCES plans(id),
            seq INTEGER,
            description TEXT NOT NULL,
            depends_on TEXT,                   -- comma-separated subtask seqs
            status TEXT DEFAULT 'pending',     -- pending | done | skipped
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grp TEXT NOT NULL,                 -- decision family, e.g. 'email_subject_style'
            variant TEXT NOT NULL,             -- the approach tried
            trials INTEGER DEFAULT 0,
            successes INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(grp, variant)
        );

        CREATE TABLE IF NOT EXISTS monitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,               -- search topic to watch
            seen_urls TEXT DEFAULT '',         -- newline-joined URLs already reported
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS usage_daily (
            day TEXT PRIMARY KEY,              -- YYYY-MM-DD
            llm_calls INTEGER DEFAULT 0,
            tool_calls INTEGER DEFAULT 0,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS finance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cash REAL,                         -- cash in the bank
            monthly_burn REAL,                 -- gross monthly spend
            mrr REAL DEFAULT 0,                -- monthly recurring revenue
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS seen_emails (
            msg_key TEXT PRIMARY KEY,          -- Message-ID (or synthetic key)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS swarm_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            topology TEXT,
            agent_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',     -- running | done | failed
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS swarm_board (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES swarm_runs(id),
            agent TEXT NOT NULL,
            entry_type TEXT NOT NULL,          -- init | finding | claim | validation | critique
            content TEXT NOT NULL,
            salience REAL DEFAULT 1.0,
            parent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS swarm_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            role TEXT DEFAULT 'worker',        -- explorer | worker | validator
            specialty TEXT,
            pheromone REAL DEFAULT 1.0,
            workload INTEGER DEFAULT 0,
            successes INTEGER DEFAULT 0,
            trials INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS swarm_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL UNIQUE,
            job_type TEXT NOT NULL,
            payload_json TEXT,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'pending',     -- pending | running | done | failed
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS swarm_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            from_agent TEXT,
            to_agent TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT,
            kind TEXT,
            failure_class TEXT,
            signal TEXT,
            tool_name TEXT,
            diagnosis TEXT,
            recovery_action TEXT,
            recovered INTEGER DEFAULT 0,
            trace_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS circuit_state (
            key TEXT PRIMARY KEY,
            state TEXT DEFAULT 'closed',
            fail_count INTEGER DEFAULT 0,
            opened_at REAL,
            last_probe REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn_id TEXT NOT NULL,
            step INTEGER,
            snapshot_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS healing_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            step INTEGER,
            failure_class TEXT,
            action TEXT,
            outcome TEXT,
            cost_ms INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    # Migrate older usage_daily rows that predate token/cost columns.
    for col, decl in (("prompt_tokens", "INTEGER DEFAULT 0"),
                      ("completion_tokens", "INTEGER DEFAULT 0"),
                      ("cost_usd", "REAL DEFAULT 0")):
        try:
            conn.execute(f"ALTER TABLE usage_daily ADD COLUMN {col} {decl}")
        except Exception:
            pass
    conn.commit()
    conn.close()


# ── REMINDERS ─────────────────────────────────────────────────────────────────

def add_reminder(text: str, due_at: str, repeat: Optional[str] = None) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO reminders (text, due_at, repeat) VALUES (?, ?, ?)",
        (text, due_at, repeat),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def get_pending_reminders() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM reminders WHERE status = 'pending' ORDER BY due_at ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_due_reminders(now_iso: Optional[str] = None) -> list:
    now_iso = now_iso or datetime.now().isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM reminders WHERE status = 'pending' AND due_at <= ? ORDER BY due_at ASC",
        (now_iso,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_reminder_status(reminder_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE reminders SET status = ? WHERE id = ?", (status, reminder_id))
    conn.commit()
    conn.close()


def reschedule_reminder(reminder_id: int, new_due_at: str):
    conn = get_conn()
    conn.execute("UPDATE reminders SET due_at = ? WHERE id = ?", (new_due_at, reminder_id))
    conn.commit()
    conn.close()


# ── GOALS ─────────────────────────────────────────────────────────────────────

def add_goal(title: str, detail: str = "", priority: int = 3) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO goals (title, detail, priority) VALUES (?, ?, ?)",
        (title, detail, priority),
    )
    conn.commit()
    gid = cur.lastrowid
    conn.close()
    return gid


def list_goals(status: str = "active") -> list:
    conn = get_conn()
    if status == "all":
        rows = conn.execute("SELECT * FROM goals ORDER BY priority ASC, updated_at DESC").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM goals WHERE status = ? ORDER BY priority ASC, updated_at DESC",
            (status,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_goal(goal_id: int, **kwargs):
    if not kwargs:
        return
    kwargs["updated_at"] = datetime.now().isoformat()
    conn = get_conn()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    conn.execute(f"UPDATE goals SET {sets} WHERE id = ?", (*kwargs.values(), goal_id))
    conn.commit()
    conn.close()


# ── LESSONS ───────────────────────────────────────────────────────────────────

def add_lesson(lesson: str, situation: str = "", tags: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO lessons (situation, lesson, tags) VALUES (?, ?, ?)",
        (situation, lesson, tags),
    )
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid


def recent_lessons(limit: int = 10) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM lessons ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── SKILLS ────────────────────────────────────────────────────────────────────

def upsert_skill(name: str, when_to_use: str, steps: str) -> int:
    conn = get_conn()
    existing = conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE skills SET when_to_use = ?, steps = ?, updated_at = ? WHERE id = ?",
            (when_to_use, steps, datetime.now().isoformat(), existing["id"]),
        )
        sid = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO skills (name, when_to_use, steps) VALUES (?, ?, ?)",
            (name, when_to_use, steps),
        )
        sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid


def list_skills() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM skills ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── APPROVALS ─────────────────────────────────────────────────────────────────

def create_approval(tool_name: str, args: dict, summary: str, kind: str = "action") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO approvals (kind, tool_name, args_json, summary) VALUES (?, ?, ?, ?)",
        (kind, tool_name, json.dumps(args), summary),
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def get_approval(approval_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_pending_approvals() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM approvals WHERE status = 'pending' ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_approval_status(approval_id: int, status: str, result: str = None):
    conn = get_conn()
    conn.execute(
        "UPDATE approvals SET status = ?, result = ?, decided_at = ? WHERE id = ?",
        (status, result, datetime.now().isoformat(), approval_id),
    )
    conn.commit()
    conn.close()


# ── PLANS / SUBTASKS ──────────────────────────────────────────────────────────

def create_plan(goal: str, rationale: str, steps: list) -> int:
    """Persist a plan and its ordered subtasks. `steps` is a list of dicts or strings."""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO plans (goal, rationale) VALUES (?, ?)", (goal, rationale)
    )
    plan_id = cur.lastrowid
    for i, step in enumerate(steps):
        if isinstance(step, dict):
            desc = step.get("description") or step.get("step") or str(step)
            depends = ",".join(str(d) for d in (step.get("depends_on") or []))
        else:
            desc, depends = str(step), ""
        conn.execute(
            "INSERT INTO subtasks (plan_id, seq, description, depends_on) VALUES (?, ?, ?, ?)",
            (plan_id, i, desc, depends),
        )
    conn.commit()
    conn.close()
    return plan_id


def get_plan(plan_id: int) -> Optional[dict]:
    conn = get_conn()
    p = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not p:
        conn.close()
        return None
    subs = conn.execute(
        "SELECT * FROM subtasks WHERE plan_id = ? ORDER BY seq ASC", (plan_id,)
    ).fetchall()
    conn.close()
    return {**dict(p), "subtasks": [dict(s) for s in subs]}


def list_open_plans() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM plans WHERE status = 'open' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_subtask(subtask_id: int, status: str, result: str = None):
    conn = get_conn()
    conn.execute(
        "UPDATE subtasks SET status = ?, result = ? WHERE id = ?",
        (status, result, subtask_id),
    )
    conn.commit()
    conn.close()


def set_plan_status(plan_id: int, status: str):
    conn = get_conn()
    conn.execute(
        "UPDATE plans SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.now().isoformat(), plan_id),
    )
    conn.commit()
    conn.close()


# ── STRATEGIES (A/B optimizer) ────────────────────────────────────────────────

def record_strategy(grp: str, variant: str, success: bool):
    conn = get_conn()
    conn.execute(
        """INSERT INTO strategies (grp, variant, trials, successes, updated_at)
           VALUES (?, ?, 1, ?, ?)
           ON CONFLICT(grp, variant) DO UPDATE SET
             trials = trials + 1,
             successes = successes + ?,
             updated_at = ?""",
        (grp, variant, 1 if success else 0, datetime.now().isoformat(),
         1 if success else 0, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def strategy_leaderboard(grp: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM strategies WHERE grp = ? ORDER BY (CAST(successes AS REAL)/MAX(trials,1)) DESC, trials DESC",
        (grp,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def all_strategies(limit: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM strategies ORDER BY trials DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── MONITORS ──────────────────────────────────────────────────────────────────

def add_monitor(topic: str) -> int:
    conn = get_conn()
    cur = conn.execute("INSERT INTO monitors (topic) VALUES (?)", (topic,))
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return mid


def list_monitors(active_only: bool = True) -> list:
    conn = get_conn()
    if active_only:
        rows = conn.execute("SELECT * FROM monitors WHERE active = 1 ORDER BY created_at DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM monitors ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deactivate_monitor(monitor_id: int):
    conn = get_conn()
    conn.execute("UPDATE monitors SET active = 0 WHERE id = ?", (monitor_id,))
    conn.commit()
    conn.close()


def mark_monitor_seen(monitor_id: int, urls: list):
    conn = get_conn()
    row = conn.execute("SELECT seen_urls FROM monitors WHERE id = ?", (monitor_id,)).fetchone()
    existing = (row["seen_urls"] if row else "") or ""
    merged = "\n".join(filter(None, existing.split("\n") + list(urls)))
    conn.execute("UPDATE monitors SET seen_urls = ? WHERE id = ?", (merged, monitor_id))
    conn.commit()
    conn.close()


# ── USAGE / BUDGET ────────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def incr_usage(llm: int = 0, tools: int = 0, prompt_tokens: int = 0,
               completion_tokens: int = 0, cost_usd: float = 0.0):
    day = _today()
    conn = get_conn()
    conn.execute(
        """INSERT INTO usage_daily (day, llm_calls, tool_calls, prompt_tokens, completion_tokens, cost_usd)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(day) DO UPDATE SET
             llm_calls = llm_calls + ?, tool_calls = tool_calls + ?,
             prompt_tokens = prompt_tokens + ?, completion_tokens = completion_tokens + ?,
             cost_usd = cost_usd + ?""",
        (day, llm, tools, prompt_tokens, completion_tokens, cost_usd,
         llm, tools, prompt_tokens, completion_tokens, cost_usd),
    )
    conn.commit()
    conn.close()


def usage_today() -> dict:
    day = _today()
    conn = get_conn()
    row = conn.execute("SELECT * FROM usage_daily WHERE day = ?", (day,)).fetchone()
    conn.close()
    return dict(row) if row else {"day": day, "llm_calls": 0, "tool_calls": 0}


# ── FINANCE ───────────────────────────────────────────────────────────────────

def set_financials(cash: float, monthly_burn: float, mrr: float = 0.0, note: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO finance_log (cash, monthly_burn, mrr, note) VALUES (?, ?, ?, ?)",
        (cash, monthly_burn, mrr, note),
    )
    conn.commit()
    fid = cur.lastrowid
    conn.close()
    return fid


def latest_financials() -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM finance_log ORDER BY created_at DESC, id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def finance_history(limit: int = 12) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM finance_log ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── SEEN EMAILS (reply-loop dedupe) ───────────────────────────────────────────

def email_seen(msg_key: str) -> bool:
    if not msg_key:
        return False
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM seen_emails WHERE msg_key = ?", (msg_key,)).fetchone()
    conn.close()
    return row is not None


def mark_email_seen(msg_key: str):
    if not msg_key:
        return
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO seen_emails (msg_key) VALUES (?)", (msg_key,))
    conn.commit()
    conn.close()


# ── ACTION LOG ────────────────────────────────────────────────────────────────

def log_action(actor: str, tool_name: str, args: dict, result: str):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO action_log (actor, tool_name, args_json, result) VALUES (?, ?, ?, ?)",
            (actor, tool_name, json.dumps(args, default=str)[:4000], str(result)[:4000]),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def recent_actions(limit: int = 15) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT actor, tool_name, substr(result,1,160) AS result, created_at "
        "FROM action_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def usage_history(days: int = 7) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM usage_daily ORDER BY day DESC LIMIT ?", (days,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── SWARM ─────────────────────────────────────────────────────────────────────

def create_swarm_run(goal: str, topology: str, agent_count: int = 0) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO swarm_runs (goal, topology, agent_count) VALUES (?, ?, ?)",
        (goal, topology, agent_count),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def finish_swarm_run(run_id: int, status: str, result: str = ""):
    conn = get_conn()
    conn.execute(
        "UPDATE swarm_runs SET status = ?, result = ?, finished_at = ? WHERE id = ?",
        (status, result, datetime.now().isoformat(), run_id),
    )
    conn.commit()
    conn.close()


def list_swarm_runs(limit: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM swarm_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def board_post(run_id: int, agent: str, entry_type: str, content: str,
               salience: float = 1.0, parent_id: int = None) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO swarm_board (run_id, agent, entry_type, content, salience, parent_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, agent, entry_type, content[:4000], salience, parent_id),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def board_read(run_id: int, limit: int = 20, min_salience: float = 0.0) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM swarm_board WHERE run_id = ? AND salience >= ? "
        "ORDER BY salience DESC, id DESC LIMIT ?",
        (run_id, min_salience, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_swarm_agent(name: str, role: str, pheromone: float = 1.0, specialty: str = ""):
    conn = get_conn()
    conn.execute(
        """INSERT INTO swarm_agents (name, role, pheromone, specialty, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
             role = ?, pheromone = ?, specialty = ?, updated_at = ?""",
        (name, role, pheromone, specialty, datetime.now().isoformat(),
         role, pheromone, specialty, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def list_swarm_agents(role: str = None) -> list:
    conn = get_conn()
    if role:
        rows = conn.execute(
            "SELECT * FROM swarm_agents WHERE role = ? ORDER BY pheromone DESC", (role,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM swarm_agents ORDER BY pheromone DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_swarm_agent_pheromone(name: str, success: bool, delta: float = 0.1):
    conn = get_conn()
    row = conn.execute("SELECT pheromone, successes, trials FROM swarm_agents WHERE name = ?", (name,)).fetchone()
    if not row:
        conn.close()
        return
    p = float(row["pheromone"])
    p = min(3.0, max(0.1, p + delta if success else p - delta * 0.5))
    conn.execute(
        "UPDATE swarm_agents SET pheromone = ?, successes = successes + ?, trials = trials + 1, updated_at = ? WHERE name = ?",
        (p, 1 if success else 0, datetime.now().isoformat(), name),
    )
    conn.commit()
    conn.close()


def enqueue_swarm_job(job_id: str, job_type: str, payload_json: str, priority: int = 5):
    conn = get_conn()
    conn.execute(
        "INSERT INTO swarm_jobs (job_id, job_type, payload_json, priority) VALUES (?, ?, ?, ?)",
        (job_id, job_type, payload_json, priority),
    )
    conn.commit()
    conn.close()


def dequeue_swarm_job() -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM swarm_jobs WHERE status = 'pending' ORDER BY priority DESC, id ASC LIMIT 1"
    ).fetchone()
    if not row:
        conn.close()
        return {}
    conn.execute(
        "UPDATE swarm_jobs SET status = 'running' WHERE job_id = ?", (row["job_id"],)
    )
    conn.commit()
    conn.close()
    import json as _json
    return {"id": row["job_id"], "type": row["job_type"], "payload": _json.loads(row["payload_json"] or "{}")}


def finish_swarm_job(job_id: str, status: str, result: str = ""):
    conn = get_conn()
    conn.execute(
        "UPDATE swarm_jobs SET status = ?, result = ?, finished_at = ? WHERE job_id = ?",
        (status, result, datetime.now().isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def post_swarm_message(run_id: int, from_agent: str, to_agent: str, content: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO swarm_messages (run_id, from_agent, to_agent, content) VALUES (?, ?, ?, ?)",
        (run_id, from_agent, to_agent, content[:4000]),
    )
    conn.commit()
    conn.close()


def get_swarm_messages(run_id: int, limit: int = 50) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM swarm_messages WHERE run_id = ? ORDER BY id DESC LIMIT ?",
        (run_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── SELF-HEALING ──────────────────────────────────────────────────────────────

def log_failure(actor: str, kind: str, failure_class: str, signal: str,
                tool_name: str = "", diagnosis: str = "", recovery_action: str = "",
                recovered: bool = False, trace_id: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO failures (actor, kind, failure_class, signal, tool_name, diagnosis, "
        "recovery_action, recovered, trace_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (actor, kind, failure_class, signal, tool_name, diagnosis, recovery_action,
         1 if recovered else 0, trace_id),
    )
    conn.commit()
    conn.close()


def list_failures(limit: int = 50) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM failures ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def recall_failures(tool_name: str = "", failure_class: str = "", limit: int = 5) -> list:
    conn = get_conn()
    q = "SELECT * FROM failures WHERE 1=1"
    params = []
    if tool_name:
        q += " AND tool_name = ?"
        params.append(tool_name)
    if failure_class:
        q += " AND failure_class = ?"
        params.append(failure_class)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_circuit_state(key: str, state: str, fail_count: int, opened_at: float = None):
    conn = get_conn()
    conn.execute(
        """INSERT INTO circuit_state (key, state, fail_count, opened_at, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET
             state = ?, fail_count = ?, opened_at = ?, updated_at = ?""",
        (key, state, fail_count, opened_at, datetime.now().isoformat(),
         state, fail_count, opened_at, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_circuit_state(key: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM circuit_state WHERE key = ?", (key,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_circuit_states() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM circuit_state ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_checkpoint(turn_id: str, step: int, snapshot_json: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO checkpoints (turn_id, step, snapshot_json) VALUES (?, ?, ?)",
        (turn_id, step, snapshot_json),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def get_latest_checkpoint(turn_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM checkpoints WHERE turn_id = ? ORDER BY id DESC LIMIT 1",
        (turn_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_checkpoints(turn_id: str, compensation_only: bool = False) -> list:
    conn = get_conn()
    if compensation_only:
        rows = conn.execute(
            "SELECT * FROM checkpoints WHERE turn_id = ? AND step = -1 ORDER BY id DESC",
            (turn_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM checkpoints WHERE turn_id = ? ORDER BY id DESC",
            (turn_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_healing_event(trace_id: str, step: int, failure_class: str, action: str,
                      outcome: str, cost_ms: int = 0):
    conn = get_conn()
    conn.execute(
        "INSERT INTO healing_events (trace_id, step, failure_class, action, outcome, cost_ms) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (trace_id, step, failure_class, action, outcome, cost_ms),
    )
    conn.commit()
    conn.close()


def list_healing_events(limit: int = 50) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM healing_events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import.
init_agent_db()

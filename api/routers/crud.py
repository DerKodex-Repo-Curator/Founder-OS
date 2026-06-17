"""Phase 2 CRUD API over existing Founder OS data."""
import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent import store, finance
from memory import sql_store
from memory.sql_store import get_conn
from agent.identity import INSTRUCTIONS_PATH, read_constitution

router = APIRouter(tags=["crud"])


def _delete_row(table: str, row_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ── Contacts ──────────────────────────────────────────────────────────────────

class ContactBody(BaseModel):
    name: str
    company: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    status: str = "prospect"
    priority: int = 3
    notes: Optional[str] = None


@router.get("/contacts")
def list_contacts():
    return {"contacts": sql_store.get_all_contacts()}


@router.post("/contacts")
def create_contact(body: ContactBody):
    cid = sql_store.add_contact(**body.model_dump())
    return sql_store.get_contact(cid)


@router.patch("/contacts/{contact_id}")
def update_contact(contact_id: int, body: ContactBody):
    if not sql_store.get_contact(contact_id):
        raise HTTPException(404, "Contact not found")
    sql_store.update_contact(contact_id, **body.model_dump())
    return sql_store.get_contact(contact_id)


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int):
    if not _delete_row("contacts", contact_id):
        raise HTTPException(404, "Contact not found")
    return {"deleted": True}


# ── Companies ─────────────────────────────────────────────────────────────────

class CompanyBody(BaseModel):
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    research_summary: Optional[str] = None
    icp_score: Optional[int] = None
    notes: Optional[str] = None


@router.get("/companies")
def list_companies():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM companies ORDER BY updated_at DESC").fetchall()
    conn.close()
    return {"companies": [dict(r) for r in rows]}


@router.post("/companies")
def create_company(body: CompanyBody):
    cid = sql_store.add_company(**body.model_dump())
    conn = get_conn()
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (cid,)).fetchone()
    conn.close()
    return dict(row)


@router.patch("/companies/{company_id}")
def update_company(company_id: int, body: CompanyBody):
    conn = get_conn()
    row = conn.execute("SELECT id FROM companies WHERE id = ?", (company_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Company not found")
    data = body.model_dump()
    data["updated_at"] = __import__("datetime").datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in data)
    conn.execute(f"UPDATE companies SET {sets} WHERE id = ?", (*data.values(), company_id))
    conn.commit()
    updated = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    conn.close()
    return dict(updated)


@router.delete("/companies/{company_id}")
def delete_company(company_id: int):
    if not _delete_row("companies", company_id):
        raise HTTPException(404, "Company not found")
    return {"deleted": True}


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskBody(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 3
    due_at: Optional[str] = None
    status: str = "pending"


@router.get("/tasks")
def list_tasks():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"tasks": [dict(r) for r in rows]}


@router.post("/tasks")
def create_task(body: TaskBody):
    tid = sql_store.add_task(body.title, body.description, body.priority, body.due_at)
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
    conn.close()
    return dict(row)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, body: TaskBody):
    conn = get_conn()
    if not conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Task not found")
    conn.execute(
        "UPDATE tasks SET title=?, description=?, priority=?, due_at=?, status=? WHERE id=?",
        (body.title, body.description, body.priority, body.due_at, body.status, task_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    if not _delete_row("tasks", task_id):
        raise HTTPException(404, "Task not found")
    return {"deleted": True}


# ── Goals ─────────────────────────────────────────────────────────────────────

class GoalBody(BaseModel):
    title: str
    detail: str = ""
    priority: int = 3
    status: str = "active"


@router.get("/goals")
def list_all_goals():
    return {"goals": store.list_goals("all")}


@router.post("/goals")
def create_goal(body: GoalBody):
    gid = store.add_goal(body.title, body.detail, body.priority)
    if body.status != "active":
        store.update_goal(gid, status=body.status)
    conn = get_conn()
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (gid,)).fetchone()
    conn.close()
    return dict(row)


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: int, body: GoalBody):
    conn = get_conn()
    if not conn.execute("SELECT id FROM goals WHERE id = ?", (goal_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Goal not found")
    conn.close()
    store.update_goal(goal_id, title=body.title, detail=body.detail,
                      priority=body.priority, status=body.status)
    conn = get_conn()
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    conn.close()
    return dict(row)


@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: int):
    if not _delete_row("goals", goal_id):
        raise HTTPException(404, "Goal not found")
    return {"deleted": True}


# ── Reminders ─────────────────────────────────────────────────────────────────

class ReminderBody(BaseModel):
    text: str
    due_at: str
    repeat: Optional[str] = None
    status: str = "pending"


@router.get("/reminders")
def list_reminders():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM reminders ORDER BY due_at ASC").fetchall()
    conn.close()
    return {"reminders": [dict(r) for r in rows]}


@router.post("/reminders")
def create_reminder(body: ReminderBody):
    rid = store.add_reminder(body.text, body.due_at, body.repeat)
    if body.status != "pending":
        store.set_reminder_status(rid, body.status)
    conn = get_conn()
    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (rid,)).fetchone()
    conn.close()
    return dict(row)


@router.patch("/reminders/{reminder_id}")
def update_reminder(reminder_id: int, body: ReminderBody):
    conn = get_conn()
    if not conn.execute("SELECT id FROM reminders WHERE id = ?", (reminder_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Reminder not found")
    conn.execute(
        "UPDATE reminders SET text=?, due_at=?, repeat=?, status=? WHERE id=?",
        (body.text, body.due_at, body.repeat, body.status, reminder_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    conn.close()
    return dict(row)


@router.delete("/reminders/{reminder_id}")
def delete_reminder(reminder_id: int):
    if not _delete_row("reminders", reminder_id):
        raise HTTPException(404, "Reminder not found")
    return {"deleted": True}


# ── Lessons ───────────────────────────────────────────────────────────────────

class LessonBody(BaseModel):
    lesson: str
    situation: str = ""
    tags: str = ""


@router.get("/lessons")
def list_lessons():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM lessons ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"lessons": [dict(r) for r in rows]}


@router.post("/lessons")
def create_lesson(body: LessonBody):
    lid = store.add_lesson(body.lesson, body.situation, body.tags)
    conn = get_conn()
    row = conn.execute("SELECT * FROM lessons WHERE id = ?", (lid,)).fetchone()
    conn.close()
    return dict(row)


@router.patch("/lessons/{lesson_id}")
def update_lesson(lesson_id: int, body: LessonBody):
    conn = get_conn()
    if not conn.execute("SELECT id FROM lessons WHERE id = ?", (lesson_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Lesson not found")
    conn.execute(
        "UPDATE lessons SET lesson=?, situation=?, tags=? WHERE id=?",
        (body.lesson, body.situation, body.tags, lesson_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    conn.close()
    return dict(row)


@router.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: int):
    if not _delete_row("lessons", lesson_id):
        raise HTTPException(404, "Lesson not found")
    return {"deleted": True}


# ── Skills ────────────────────────────────────────────────────────────────────

class SkillBody(BaseModel):
    name: str
    when_to_use: str = ""
    steps: str = ""


@router.get("/skills")
def list_skills_api():
    return {"skills": store.list_skills()}


@router.post("/skills")
def create_skill(body: SkillBody):
    sid = store.upsert_skill(body.name, body.when_to_use, body.steps)
    conn = get_conn()
    row = conn.execute("SELECT * FROM skills WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return dict(row)


@router.patch("/skills/{skill_id}")
def update_skill(skill_id: int, body: SkillBody):
    conn = get_conn()
    if not conn.execute("SELECT id FROM skills WHERE id = ?", (skill_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Skill not found")
    conn.execute(
        "UPDATE skills SET name=?, when_to_use=?, steps=?, updated_at=? WHERE id=?",
        (body.name, body.when_to_use, body.steps,
         __import__("datetime").datetime.now().isoformat(), skill_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
    conn.close()
    return dict(row)


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int):
    if not _delete_row("skills", skill_id):
        raise HTTPException(404, "Skill not found")
    return {"deleted": True}


# ── Approvals ─────────────────────────────────────────────────────────────────

@router.get("/approvals")
def list_approvals():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM approvals ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return {"approvals": [dict(r) for r in rows]}


@router.post("/approvals/{approval_id}/approve")
def approve_action(approval_id: int):
    approval = store.get_approval(approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")
    if approval["status"] != "pending":
        raise HTTPException(400, f"Approval already {approval['status']}")
    store.set_approval_status(approval_id, "approved")
    return store.get_approval(approval_id)


@router.post("/approvals/{approval_id}/reject")
def reject_action(approval_id: int):
    approval = store.get_approval(approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")
    if approval["status"] != "pending":
        raise HTTPException(400, f"Approval already {approval['status']}")
    store.set_approval_status(approval_id, "rejected")
    return store.get_approval(approval_id)


# ── Finance ───────────────────────────────────────────────────────────────────

class FinanceBody(BaseModel):
    cash: float
    monthly_burn: float
    mrr: float = 0.0
    note: str = ""


@router.get("/finance")
def get_finance():
    return finance.summary()


@router.post("/finance")
def set_finance(body: FinanceBody):
    store.set_financials(body.cash, body.monthly_burn, body.mrr, body.note)
    return finance.summary()


# ── Instructions ──────────────────────────────────────────────────────────────

class InstructionsBody(BaseModel):
    content: str


@router.get("/instructions")
def get_instructions():
    content = ""
    if os.path.isfile(INSTRUCTIONS_PATH):
        with open(INSTRUCTIONS_PATH, encoding="utf-8") as f:
            content = f.read()
    return {"instructions": content, "constitution": read_constitution()}


@router.put("/instructions")
def set_instructions(body: InstructionsBody):
    os.makedirs(os.path.dirname(INSTRUCTIONS_PATH), exist_ok=True)
    with open(INSTRUCTIONS_PATH, "w", encoding="utf-8") as f:
        f.write(body.content)
    return {"saved": True, "length": len(body.content)}

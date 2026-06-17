"""Context Space assets API — upload, links, notes."""
import mimetypes
import os
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from memory import context_store
from context import ingest

router = APIRouter(tags=["assets"])


class LinkCreate(BaseModel):
    url: str
    title: str = ""


class NoteCreate(BaseModel):
    title: str = ""
    text: str


@router.post("/spaces/{space_id}/assets")
async def upload_asset(
    space_id: int,
    file: UploadFile = File(...),
    title: str = Form(""),
):
    space = context_store.get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    filename = file.filename or "upload"
    mime = file.content_type or mimetypes.guess_type(filename)[0] or ""
    kind = ingest.detect_kind(filename, mime)

    asset = context_store.create_asset(
        space_id=space_id,
        kind=kind,
        title=title or filename,
        mime=mime,
        status="pending",
    )
    dest = context_store.asset_storage_path(space_id, asset["id"], filename)
    raw = await file.read()
    with open(dest, "wb") as f:
        f.write(raw)
    context_store.update_asset(asset["id"], source_path=dest)
    ingest.ingest_asset_async(asset["id"])
    return context_store.get_asset(asset["id"])


@router.post("/spaces/{space_id}/links")
def add_link(space_id: int, body: LinkCreate):
    space = context_store.get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    asset = context_store.create_asset(
        space_id=space_id,
        kind="link",
        title=body.title or body.url,
        url=body.url,
        status="pending",
    )
    ingest.ingest_asset_async(asset["id"])
    return context_store.get_asset(asset["id"])


@router.post("/spaces/{space_id}/notes")
def add_note(space_id: int, body: NoteCreate):
    space = context_store.get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if not (body.text or "").strip():
        raise HTTPException(status_code=400, detail="Note text is required")
    asset = context_store.create_asset(
        space_id=space_id,
        kind="note",
        title=body.title or "Note",
        extracted_text=body.text.strip(),
        status="pending",
    )
    ingest.ingest_asset_async(asset["id"])
    return context_store.get_asset(asset["id"])


@router.get("/assets/{asset_id}")
def get_asset(asset_id: int):
    asset = context_store.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: int):
    asset = context_store.delete_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    ingest.delete_asset_vectors(asset_id)
    return {"deleted": True, "asset_id": asset_id}


@router.post("/assets/{asset_id}/reingest")
def reingest_asset(asset_id: int):
    asset = context_store.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    ingest.ingest_asset_async(asset_id)
    return {"asset_id": asset_id, "status": "processing"}


@router.delete("/aliases/{alias_id}")
def delete_alias(alias_id: int):
    if not context_store.delete_alias(alias_id):
        raise HTTPException(status_code=404, detail="Alias not found")
    return {"deleted": True}

"""Context Spaces CRUD API."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from memory import context_store

router = APIRouter(prefix="/spaces", tags=["spaces"])


class SpaceCreate(BaseModel):
    name: str
    description: str = ""


class SpaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AliasCreate(BaseModel):
    alias: str


@router.get("")
def list_spaces():
    return {"spaces": context_store.list_spaces()}


@router.post("")
def create_space(body: SpaceCreate):
    try:
        space = context_store.create_space(body.name, body.description)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return space


@router.get("/{space_id}")
def get_space(space_id: int):
    space = context_store.get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    assets = context_store.list_assets(space_id)
    aliases = context_store.list_aliases(space_id)
    return {"space": space, "assets": assets, "aliases": aliases}


@router.patch("/{space_id}")
def update_space(space_id: int, body: SpaceUpdate):
    try:
        space = context_store.update_space(space_id, body.name, body.description)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


@router.delete("/{space_id}")
def delete_space(space_id: int):
    from context.ingest import delete_asset_vectors
    assets = context_store.list_assets(space_id)
    for a in assets:
        delete_asset_vectors(a["id"])
    if not context_store.delete_space(space_id):
        raise HTTPException(status_code=404, detail="Space not found")
    return {"deleted": True}


@router.get("/{space_id}/aliases")
def list_aliases(space_id: int):
    if not context_store.get_space(space_id):
        raise HTTPException(status_code=404, detail="Space not found")
    return {"aliases": context_store.list_aliases(space_id)}


@router.post("/{space_id}/aliases")
def add_alias(space_id: int, body: AliasCreate):
    if not context_store.get_space(space_id):
        raise HTTPException(status_code=404, detail="Space not found")
    try:
        alias = context_store.add_alias(space_id, body.alias)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return alias


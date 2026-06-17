"""Tools for querying Context Spaces from the agent."""
from agent.registry import register
from memory import context_store
from context import resolver


@register(
    name="list_context_spaces",
    description="List all Context Spaces (named knowledge buckets) with asset counts. "
                "Use when the user asks what contexts/projects/spaces are available.",
    parameters={"type": "object", "properties": {}},
    category="research",
)
def list_context_spaces():
    spaces = context_store.list_spaces()
    return {
        "spaces": [
            {
                "id": s["id"],
                "name": s["name"],
                "description": s.get("description") or "",
                "asset_count": s.get("asset_count", 0),
            }
            for s in spaces
        ],
        "count": len(spaces),
    }


@register(
    name="get_context_space",
    description="Get full details of a Context Space by name, including assets and aliases.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Exact or case-insensitive space name."},
        },
        "required": ["name"],
    },
    category="research",
)
def get_context_space(name):
    space = context_store.get_space_by_name(name)
    if not space:
        return {"error": f"No context space named '{name}'"}
    assets = context_store.list_assets(space["id"])
    aliases = context_store.list_aliases(space["id"])
    return {
        "space": {
            "id": space["id"],
            "name": space["name"],
            "description": space.get("description") or "",
        },
        "assets": [
            {
                "id": a["id"],
                "kind": a["kind"],
                "title": a.get("title") or "",
                "status": a.get("status"),
                "url": a.get("url") or "",
            }
            for a in assets
        ],
        "aliases": [al["alias"] for al in aliases],
    }


@register(
    name="search_context",
    description="Search within Context Spaces for relevant knowledge. Optionally restrict to one space by name. "
                "Use when you need project-specific background (e.g. about Stamped, a client, a deal).",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "space_name": {
                "type": "string",
                "description": "Optional: restrict search to this context space name.",
            },
            "k": {"type": "integer", "description": "Number of passages (default 6)."},
        },
        "required": ["query"],
    },
    category="research",
)
def search_context(query, space_name=None, k=6):
    try:
        k = max(1, min(int(k or 6), 12))
    except (TypeError, ValueError):
        k = 6

    space_id = None
    if space_name:
        space = context_store.get_space_by_name(space_name)
        if not space:
            return {"error": f"No context space named '{space_name}'"}
        space_id = space["id"]
        chunks = resolver.retrieve_context_chunks(query, space_id, k=k)
        space_label = space["name"]
    else:
        result = resolver.resolve(query)
        if result.get("chosen"):
            space_id = result["chosen"]["id"]
            space_label = result["chosen"]["name"]
            chunks = resolver.retrieve_context_chunks(query, space_id, k=k)
        else:
            from memory import vector_store
            hits = vector_store.search("documents", query, n_results=k)
            chunks = [h for h in hits if (h.get("metadata") or {}).get("space_id")]
            space_label = "multiple"

    passages = []
    for h in chunks:
        meta = h.get("metadata") or {}
        passages.append({
            "space": meta.get("space_name", space_label),
            "source": meta.get("source", "?"),
            "text": h.get("text", "")[:800],
        })
    return {
        "query": query,
        "space": space_label,
        "passages": passages,
        "count": len(passages),
    }

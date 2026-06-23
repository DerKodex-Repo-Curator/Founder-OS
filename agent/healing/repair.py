"""Local argument repair and output schema validation."""
import json
import logging
import re

from agent import registry

logger = logging.getLogger(__name__)


def repair_args(tool_name: str, args: dict, error_msg: str) -> dict:
    """Attempt to fix malformed tool arguments from schema + error message."""
    tool = registry.get(tool_name)
    if not tool:
        return args or {}
    args = dict(args or {})
    schema = tool.parameters or {}
    props = schema.get("properties", {})
    required = schema.get("required", [])

    # Extract missing field names from error
    missing = re.findall(r"['\"]?(\w+)['\"]?\s*(?:is required|missing|required)", error_msg, re.I)
    missing += re.findall(r"argument:\s*['\"](\w+)['\"]", error_msg, re.I)
    missing += re.findall(r"missing.*?['\"](\w+)['\"]", error_msg, re.I)
    for field in missing:
        if field in props and field not in args:
            ptype = props[field].get("type", "string")
            args[field] = "" if ptype == "string" else ([] if ptype == "array" else 0)

    # Strip unknown keys not in schema
    allowed = set(props.keys())
    args = {k: v for k, v in args.items() if k in allowed}

    # Ensure required fields have defaults
    for r in required:
        if r not in args:
            ptype = props.get(r, {}).get("type", "string")
            if ptype == "string":
                args[r] = ""
            elif ptype == "integer":
                args[r] = 0
            elif ptype == "array":
                args[r] = []
            elif ptype == "object":
                args[r] = {}

    return args


def validate_json_output(text: str) -> tuple:
    """Return (parsed_dict|None, repaired_text|None)."""
    if not text:
        return None, None
    clean = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean), None
    except json.JSONDecodeError:
        pass
    # Try to extract first JSON object
    match = re.search(r"\{[\s\S]*\}", clean)
    if match:
        try:
            return json.loads(match.group()), match.group()
        except json.JSONDecodeError:
            pass
    return None, None


def repair_json_output(text: str) -> dict:
    """Parse or auto-repair JSON from LLM output."""
    parsed, repaired = validate_json_output(text)
    if parsed is not None:
        return parsed
    return {"error": "unparseable_json", "raw": (text or "")[:500]}

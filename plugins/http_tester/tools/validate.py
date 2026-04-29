"""validate — Validiert JSON gegen ein Schema (JSON Schema Draft-07)."""
import json
from typing import Any, Dict, List

from hydrahive.tools.base import Tool, ToolContext, ToolResult

try:
    from jsonschema import validate, ValidationError, Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def _get_schema_errors(data: Any, schema: Dict, path: str = "") -> List[str]:
    """Rekursive Schema-Validierung ohne jsonschema library."""
    errors = []
    
    if not isinstance(schema, dict):
        return errors
    
    # Type check
    if "type" in schema:
        expected_types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        actual_type = type(data).__name__
        
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        
        matched = False
        for exp in expected_types:
            if exp in type_map and isinstance(data, type_map[exp]):
                matched = True
                break
        
        if not matched:
            errors.append(f"{path}: erwartet {expected_types}, bekommen {actual_type}")
            return errors
    
    # Object validation
    if isinstance(data, dict) and schema.get("type") in ["object", None]:
        props = schema.get("properties", {})
        required = schema.get("required", [])
        
        for req in required:
            if req not in data:
                errors.append(f"{path}.{req}: erforderlich aber fehlt")
        
        for key, prop_schema in props.items():
            if key in data:
                child_errors = _get_schema_errors(data[key], prop_schema, f"{path}.{key}")
                errors.extend(child_errors)
    
    # Array validation
    if isinstance(data, list) and schema.get("type") == "array":
        items_schema = schema.get("items", {})
        if items_schema:
            for i, item in enumerate(data[:10]):  # Limit check
                child_errors = _get_schema_errors(item, items_schema, f"{path}[{i}]")
                errors.extend(child_errors)
    
    return errors


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    json_data = args.get("json", "")
    schema = args.get("schema", {})
    
    # Parse JSON
    try:
        data = json.loads(json_data) if isinstance(json_data, str) else json_data
    except json.JSONDecodeError as e:
        return ToolResult.fail(f"JSON ungültig: {e}")
    
    if not HAS_JSONSCHEMA:
        # Use simple validation
        errors = _get_schema_errors(data, schema)
        
        if errors:
            return ToolResult.ok({
                "valid": False,
                "errors": errors[:20],
                "error_count": len(errors),
                "note": "Einfache Validierung (jsonschema nicht installiert)",
            })
        else:
            return ToolResult.ok({
                "valid": True,
                "errors": [],
                "note": "✅ JSON entspricht Schema (Einfache Validierung)",
            })
    
    # Use jsonschema library
    try:
        validate(instance=data, schema=schema)
        return ToolResult.ok({
            "valid": True,
            "errors": [],
        })
    except ValidationError as e:
        return ToolResult.ok({
            "valid": False,
            "errors": [str(e.message)],
            "error_path": list(e.path),
        })


TOOL = Tool(
    name="validate",
    description="Validiert JSON gegen ein JSON Schema. Prüft Types, Required Fields, etc.",
    schema={
        "type": "object",
        "properties": {
            "json": {
                "type": ["object", "string"],
                "description": "JSON Object oder String zu validieren",
            },
            "schema": {
                "type": "object",
                "description": "JSON Schema gegen das validiert wird",
            },
        },
        "required": ["json"],
    },
    execute=_execute,
)

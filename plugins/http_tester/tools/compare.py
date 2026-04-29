"""compare — Vergleicht zwei JSON-Objekte/Schemas."""
import json
from deepdiff import DeepDiff

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    json1 = args.get("json1", "")
    json2 = args.get("json2", "")
    ignore_order = args.get("ignore_order", False)
    ignore_keys = args.get("ignore_keys", [])
    
    # Parse JSON inputs
    try:
        obj1 = json.loads(json1) if isinstance(json1, str) else json1
    except json.JSONDecodeError as e:
        return ToolResult.fail(f"json1 ungültig: {e}")
    
    try:
        obj2 = json.loads(json2) if isinstance(json2, str) else json2
    except json.JSONDecodeError as e:
        return ToolResult.fail(f"json2 ungültig: {e}")
    
    # Compare
    try:
        diff = DeepDiff(obj1, obj2, ignore_order=ignore_order)
        
        if not diff:
            return ToolResult.ok({
                "equal": True,
                "differences": {},
                "summary": "✅ Objekte sind identisch",
            })
        
        # Format differences
        differences = {}
        for change_type, changes in diff.items():
            if change_type == "dictionary_item_removed":
                differences["removed_keys"] = list(changes.keys())
            elif change_type == "dictionary_item_added":
                differences["added_keys"] = list(changes.keys())
            elif change_type == "values_changed":
                differences["changed_values"] = {
                    k: {"old": v.get("old_value"), "new": v.get("new_value")}
                    for k, v in list(changes.items())[:10]
                }
            elif change_type == "type_changes":
                differences["type_changes"] = list(changes.keys())
            elif change_type == "iterable_item_removed":
                differences["removed_items"] = [str(c) for c in changes[:5]]
            elif change_type == "iterable_item_added":
                differences["added_items"] = [str(c) for c in changes[:5]]
        
        return ToolResult.ok({
            "equal": False,
            "differences": differences,
            "summary": f"❌ {len(list(diff.keys()))} Unterschiede gefunden",
            "raw_diff": str(diff)[:500],
        })
        
    except Exception as e:
        return ToolResult.fail(f"Vergleich fehlgeschlagen: {e}")


TOOL = Tool(
    name="compare",
    description="Vergleicht zwei JSON-Objekte. Zeigt Unterschiede in Keys, Values, Types.",
    schema={
        "type": "object",
        "properties": {
            "json1": {
                "type": ["object", "string"],
                "description": "Erstes JSON (Object oder String)",
            },
            "json2": {
                "type": ["object", "string"],
                "description": "Zweites JSON (Object oder String)",
            },
            "ignore_order": {
                "type": "boolean",
                "description": "Array-Reihenfolge ignorieren (default: false)",
            },
        },
        "required": ["json1", "json2"],
    },
    execute=_execute,
)

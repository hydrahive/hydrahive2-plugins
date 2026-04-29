"""compare — Vergleicht zwei JSON-Objekte."""
import json

from hydrahive.tools.base import Tool, ToolContext, ToolResult


try:
    from deepdiff import DeepDiff
    HAS_DEEP_DIFF = True
except ImportError:
    HAS_DEEP_DIFF = False


def _simple_compare(obj1, obj2, path="root"):
    """Einfacher JSON-Vergleich ohne deepdiff."""
    differences = []
    
    t1 = type(obj1).__name__
    t2 = type(obj2).__name__
    
    if t1 != t2:
        differences.append(f"{path}: Typ {t1} vs {t2}")
        return differences
    
    if isinstance(obj1, dict):
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())
        
        if keys1 != keys2:
            only_in_1 = keys1 - keys2
            only_in_2 = keys2 - keys1
            if only_in_1:
                differences.append(f"{path}: fehlende Keys: {list(only_in_1)}")
            if only_in_2:
                differences.append(f"{path}: zusätzliche Keys: {list(only_in_2)}")
        
        for key in keys1 & keys2:
            differences.extend(_simple_compare(obj1[key], obj2[key], f"{path}.{key}"))
    
    elif isinstance(obj1, list):
        if len(obj1) != len(obj2):
            differences.append(f"{path}: Länge {len(obj1)} vs {len(obj2)}")
        for i in range(min(len(obj1), len(obj2))):
            differences.extend(_simple_compare(obj1[i], obj2[i], f"{path}[{i}]"))
    
    else:
        if obj1 != obj2:
            differences.append(f"{path}: {obj1} vs {obj2}")
    
    return differences


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    json1 = args.get("json1", "")
    json2 = args.get("json2", "")
    ignore_order = args.get("ignore_order", False)
    
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
    if HAS_DEEP_DIFF:
        try:
            diff = DeepDiff(obj1, obj2, ignore_order=ignore_order)
            
            if not diff:
                return ToolResult.ok({
                    "equal": True,
                    "differences": {},
                    "summary": "✅ Objekte sind identisch",
                })
            
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
            
            return ToolResult.ok({
                "equal": False,
                "differences": differences,
                "summary": f"❌ {len(list(diff.keys()))} Unterschiede gefunden",
            })
            
        except Exception as e:
            return ToolResult.fail(f"Vergleich fehlgeschlagen: {e}")
    else:
        # Fallback ohne deepdiff
        diffs = _simple_compare(obj1, obj2)
        
        if not diffs:
            return ToolResult.ok({
                "equal": True,
                "differences": {},
                "note": "Einfache Vergleich (deepdiff nicht installiert)",
            })
        
        return ToolResult.ok({
            "equal": False,
            "differences": {"diff_count": len(diffs), "details": diffs[:20]},
            "summary": f"❌ {len(diffs)} Unterschiede gefunden",
            "note": "Einfache Vergleich (deepdiff nicht installiert)",
        })


TOOL = Tool(
    name="compare",
    description="Vergleicht zwei JSON-Objekte. Zeigt Unterschiede in Keys, Values, Types.",
    schema={
        "type": "object",
        "properties": {
            "json1": {
                "type": ["object", "string"],
                "description": "Erstes JSON",
            },
            "json2": {
                "type": ["object", "string"],
                "description": "Zweites JSON",
            },
            "ignore_order": {
                "type": "boolean",
                "description": "Array-Reihenfolge ignorieren",
            },
        },
        "required": ["json1", "json2"],
    },
    execute=_execute,
)

"""find — Findet Dateien nach Name-Pattern."""
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    name = args.get("name", "")
    pattern = args.get("pattern", "")
    extensions = args.get("extensions", [])
    max_depth = int(args.get("max_depth", 10))
    sort_by = args.get("sort_by", "name")  # name, size, modified
    
    if not name and not pattern:
        return ToolResult.fail("Entweder 'name' oder 'pattern' ist erforderlich")
    
    root = Path(path_arg).resolve()
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    # Build search term
    search_term = name or pattern
    
    try:
        all_files = list(root.rglob("*"))
    except Exception as e:
        return ToolResult.fail(f"Glob-Fehler: {e}")
    
    # Filter
    results = []
    for f in all_files:
        if not f.is_file():
            continue
        
        # Check depth
        try:
            rel = f.relative_to(root)
            if len(rel.parts) > max_depth:
                continue
        except ValueError:
            continue
        
        # Skip hidden/binary dirs
        if any(part.startswith(".") or part in {
            "node_modules", "__pycache__", "venv", ".venv", "dist", "build", "target"
        } for part in rel.parts):
            continue
        
        # Match
        filename = f.name.lower()
        if name.lower() in filename or (pattern and _match_glob(filename, pattern.lower())):
            
            # Extension filter
            if extensions and f.suffix not in [f".{e.strip('.')}" for e in extensions]:
                continue
            
            try:
                stat = f.stat()
                results.append({
                    "path": str(rel),
                    "name": f.name,
                    "extension": f.suffix,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
            except Exception:
                pass
    
    # Sort
    if sort_by == "name":
        results.sort(key=lambda x: x["name"])
    elif sort_by == "size":
        results.sort(key=lambda x: x["size"], reverse=True)
    elif sort_by == "modified":
        results.sort(key=lambda x: x["modified"], reverse=True)
    
    # Limit
    limit = int(args.get("limit", 50))
    results = results[:limit]
    
    return ToolResult.ok({
        "path": str(root),
        "search": search_term,
        "total_found": len(results),
        "shown": len(results),
        "results": results,
    })


def _match_glob(filename: str, pattern: str) -> bool:
    """Einfacher Glob-Match für * und ?"""
    import fnmatch
    return fnmatch.fnmatch(filename, f"*{pattern}*")


TOOL = Tool(
    name="find",
    description="Findet Dateien nach Name oder Pattern.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Projekt (default: Workspace)",
            },
            "name": {
                "type": "string",
                "description": "Teil des Dateinamens",
            },
            "pattern": {
                "type": "string",
                "description": "Glob-Pattern (z.B. '*.py')",
            },
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: Nur diese Endungen",
            },
            "sort_by": {
                "type": "string",
                "enum": ["name", "size", "modified"],
                "description": "Sortierung (default: name)",
            },
            "limit": {
                "type": "integer",
                "description": "Max Ergebnisse (default: 50)",
            },
            "max_depth": {
                "type": "integer",
                "description": "Max Verzeichnis-Tiefe (default: 10)",
            },
        },
        "required": [],
    },
    execute=_execute,
)

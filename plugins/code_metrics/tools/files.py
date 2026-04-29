"""files — Listet alle Dateien mit Größen und Metriken."""
from pathlib import Path
from collections import defaultdict

from hydrahive.tools.base import Tool, ToolContext, ToolResult


def _format_size(size: int) -> str:
    """Formatiert Bytes in lesbare Größe."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    pattern = args.get("pattern", "**/*")
    max_depth = int(args.get("max_depth", 10))
    sort_by = args.get("sort_by", "size")  # size, name, modified
    
    root = Path(path_arg).resolve()
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    # Get all files
    try:
        files = [f for f in root.glob(pattern) if f.is_file()]
    except Exception as e:
        return ToolResult.fail(f"Glob-Fehler: {e}")
    
    # Filter hidden dirs, etc.
    files = [f for f in files if not any(
        part.startswith(".") or part in {"node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
        for part in f.relative_to(root).parts
    )]
    
    # Build file list with metadata
    file_list = []
    for f in files:
        try:
            stat = f.stat()
            rel_path = str(f.relative_to(root))
            depth = len(rel_path.split("/"))
            
            if depth > max_depth:
                continue
            
            file_list.append({
                "path": rel_path,
                "size": stat.st_size,
                "size_formatted": _format_size(stat.st_size),
                "modified": stat.st_mtime,
                "extension": f.suffix or "(none)",
            })
        except Exception:
            pass
    
    # Sort
    if sort_by == "size":
        file_list.sort(key=lambda x: x["size"], reverse=True)
    elif sort_by == "name":
        file_list.sort(key=lambda x: x["path"])
    elif sort_by == "modified":
        file_list.sort(key=lambda x: x["modified"], reverse=True)
    
    # Limit
    limit = int(args.get("limit", 100))
    file_list = file_list[:limit]
    
    # Stats
    total_size = sum(f["size"] for f in file_list)
    by_ext = defaultdict(lambda: {"count": 0, "size": 0})
    for f in file_list:
        by_ext[f["extension"]]["count"] += 1
        by_ext[f["extension"]]["size"] += f["size"]
    
    extensions = sorted(by_ext.items(), key=lambda x: x[1]["size"], reverse=True)[:10]
    
    return ToolResult.ok({
        "root": str(root),
        "pattern": pattern,
        "total_found": len(files),
        "shown": len(file_list),
        "total_size": total_size,
        "total_size_formatted": _format_size(total_size),
        "files": file_list,
        "top_extensions": [
            {"extension": ext, **stats, "size_formatted": _format_size(stats["size"])}
            for ext, stats in extensions
        ],
    })


TOOL = Tool(
    name="files",
    description="Listet alle Dateien mit Größen, sortiert nach Größe/Name/Datum.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Projekt (default: Workspace)",
            },
            "pattern": {
                "type": "string",
                "description": "Glob-Pattern (default: **/*)",
            },
            "sort_by": {
                "type": "string",
                "enum": ["size", "name", "modified"],
                "description": "Sortierung (default: size)",
            },
            "limit": {
                "type": "integer",
                "description": "Max Dateien anzuzeigen (default: 100)",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximale Verzeichnis-Tiefe (default: 10)",
            },
        },
        "required": [],
    },
    execute=_execute,
)

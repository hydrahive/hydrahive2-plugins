"""find — Findet Dateien nach Name-Pattern."""

from hydrahive.tools._path import PathOutsideWorkspace
try:  # Kern mit verknüpften Projekten: lesen auch dort (nur lesen)
    from hydrahive.tools._path import read_path
except ImportError:  # älterer Kern: nur der eigene Arbeitsordner
    from hydrahive.tools._path import safe_path

    def read_path(ctx, requested):
        return safe_path(ctx.workspace, requested)
import asyncio

from hydrahive.tools.base import Tool, ToolContext, ToolResult

try:  # im Betrieb als Paket geladen (plugins/loader.py)
    from file_search.tools import _walk
except ImportError:  # Tests laden die Datei einzeln
    import importlib.util as _ilu
    import pathlib as _pl
    import sys as _sys
    _walk = _sys.modules.get("file_search_walk")
    if _walk is None:
        _spec = _ilu.spec_from_file_location("file_search_walk", _pl.Path(__file__).with_name("_walk.py"))
        _walk = _ilu.module_from_spec(_spec)
        _sys.modules["file_search_walk"] = _walk      # dataclass braucht das Modul in sys.modules
        _spec.loader.exec_module(_walk)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    name = args.get("name", "")
    pattern = args.get("pattern", "")
    extensions = args.get("extensions", [])
    max_depth = int(args.get("max_depth", 10))
    sort_by = args.get("sort_by", "name")  # name, size, modified
    
    if not name and not pattern:
        return ToolResult.fail("Entweder 'name' oder 'pattern' ist erforderlich")
    
    try:
    
        root = read_path(ctx, path_arg)
    
    except PathOutsideWorkspace as e:
    
        return ToolResult.fail(str(e))
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    search_term = name or pattern
    exts = {f".{e.strip('.')}" for e in extensions} if extensions else None

    def keep(f) -> bool:
        filename = f.name.lower()
        if not (name.lower() in filename if name else False) and not (pattern and _match_glob(filename, pattern.lower())):
            return False
        return exts is None or f.suffix in exts

    # Begrenzter Lauf im Worker-Thread (_walk.py): keine Mounts/Symlink-Ordner, Zeit- und Eintragsgrenze.
    walked = await asyncio.to_thread(_walk.walk, root, max_depth=max_depth, keep=keep)

    results = []
    for f in walked.files:
        try:
            stat = f.stat()
            results.append({
                "path": str(f.relative_to(root)),
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
    total_found = len(results)
    results = results[:limit]

    out = {
        "path": str(root),
        "search": search_term,
        "total_found": total_found,
        "shown": len(results),
        "results": results,
    }
    if walked.stopped:
        out["stopped"] = f"{walked.stopped} erreicht – Ergebnis unvollständig, Pfad/max_depth enger fassen"
    if walked.skipped_mounts:
        out["skipped_mounts"] = walked.skipped_mounts[:10]
    return ToolResult.ok(out)


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

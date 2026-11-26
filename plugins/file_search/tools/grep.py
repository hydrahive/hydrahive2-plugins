"""grep — Durchsucht Dateien nach Regex-Pattern."""
import asyncio
import re
from pathlib import Path

from hydrahive.tools._path import PathOutsideWorkspace
try:  # Kern mit verknüpften Projekten: lesen auch dort (nur lesen)
    from hydrahive.tools._path import read_path
except ImportError:  # älterer Kern: nur der eigene Arbeitsordner
    from hydrahive.tools._path import safe_path

    def read_path(ctx, requested):
        return safe_path(ctx.workspace, requested)
from hydrahive.tools.base import Tool, ToolContext, ToolResult

try:  # im Betrieb als Paket geladen (plugins/loader.py)
    from file_search.tools import _walk
except ModuleNotFoundError as _e:  # Tests laden die Datei einzeln – echte Fehler in _walk.py nicht verschlucken
    if _e.name != "file_search":
        raise
    import importlib.util as _ilu
    import pathlib as _pl
    import sys as _sys
    _walk = _sys.modules.get("file_search_walk")
    if _walk is None:
        _spec = _ilu.spec_from_file_location("file_search_walk", _pl.Path(__file__).with_name("_walk.py"))
        _walk = _ilu.module_from_spec(_spec)
        _sys.modules["file_search_walk"] = _walk      # dataclass braucht das Modul in sys.modules
        _spec.loader.exec_module(_walk)



# Hartes Sicherheitsnetz gegen Event-Loop-Blockaden (Vorfall 2026-11-19: ein
# grep über einen großen Ordner ohne Limits hat read_text() synchron im
# Event-Loop-Thread laufen lassen -> Discord-Heartbeat >590s blockiert ->
# kompletter Server-Hänger, musste hart neu gestartet werden).
MAX_FILE_BYTES = 2_000_000       # Dateien größer als 2 MB überspringen (Binaries/Logs)
MAX_FILES_TO_SEARCH = 2_000      # Harte Obergrenze unabhängig vom max_results-Wert
MAX_CONCURRENT_READS = 32        # Begrenzte Parallelität statt unbegrenztem gather()


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    pattern = args.get("pattern", "")
    extensions = args.get("extensions", [])
    case_sensitive = args.get("case_sensitive", True)
    max_results = int(args.get("max_results", 100))
    context = int(args.get("context", 0))  # Lines around match
    
    if not pattern:
        return ToolResult.fail("Pattern ist erforderlich")
    
    try:
    
        root = read_path(ctx, path_arg)
    
    except PathOutsideWorkspace as e:
    
        return ToolResult.fail(str(e))
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    # Begrenzter Lauf im Worker-Thread (_walk.py): keine Mounts/Symlink-Ordner, Zeit- und Eintragsgrenze. Vorher
    # root.glob("**/*") synchron im Event-Loop, auch durch .git/node_modules und Netzlaufwerke.
    exts = {f".{e.strip('.')}" for e in extensions} if extensions else None
    walked = await asyncio.to_thread(_walk.walk, root, max_depth=50,
                                     keep=(lambda f: f.suffix in exts) if exts else None)
    files = walked.files
    files_total_found = len(files)
    truncated_by_file_limit = files_total_found > MAX_FILES_TO_SEARCH
    files = files[:MAX_FILES_TO_SEARCH]

    # Compile regex
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except Exception as e:
        return ToolResult.fail(f"Ungültiges Regex: {e}")
    
    # Search in files. Das eigentliche Lesen+Durchsuchen ist blockierendes,
    # synchrones IO/CPU-Code -> läuft über asyncio.to_thread in einem Worker-
    # Thread, NIE direkt im Event-Loop-Thread. Sonst friert ein großer/teurer
    # Aufruf den kompletten Server ein (Discord, API, alle Sessions).
    def _search_file_sync(path: Path) -> dict:
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                return {"file": str(path), "matches": [], "skipped": "zu groß"}
            content = path.read_text(errors="ignore")
            lines = content.split("\n")
            matches = []
            
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    match_info = {
                        "line": i,
                        "content": line[:200],  # Truncate long lines
                    }
                    
                    # Add context lines
                    if context > 0:
                        start = max(0, i - context - 1)
                        end = min(len(lines), i + context)
                        match_info["context"] = [
                            {"line": j + 1, "content": lines[j][:200]}
                            for j in range(start, end)
                            if j != i - 1
                        ]
                    
                    matches.append(match_info)
                    
                    if len(matches) >= max_results:
                        break
            
            return {"file": str(path), "matches": matches}
        except Exception:
            return {"file": str(path), "matches": [], "error": True}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_READS)

    async def search_file(path: Path) -> dict:
        async with semaphore:
            return await asyncio.to_thread(_search_file_sync, path)

    results = await asyncio.gather(*[search_file(f) for f in files])
    
    # Filter and aggregate
    total_matches = 0
    files_with_matches = []
    for r in results:
        if r["matches"]:
            files_with_matches.append(r)
            total_matches += len(r["matches"])
    
    return ToolResult.ok({
        "path": str(root),
        "pattern": pattern,
        "extensions": extensions or None,
        "files_searched": len(files),
        "files_found_total": files_total_found,
        "files_truncated": truncated_by_file_limit,
        "files_with_matches": len(files_with_matches),
        "total_matches": total_matches,
        "results_limited": total_matches >= max_results,
        "matches": files_with_matches[:20],  # Top 20 files
        **({"stopped": f"{walked.stopped} erreicht – nicht alle Dateien durchsucht"} if walked.stopped else {}),
        **({"skipped_mounts": walked.skipped_mounts[:10]} if walked.skipped_mounts else {}),
        **({"skipped_links": walked.skipped_links[:10]} if walked.skipped_links else {}),
    })


TOOL = Tool(
    name="grep",
    description=("Durchsucht Dateien nach Regex-Pattern. Gibt Datei, Zeile und Content zurück. Versteckte Dateien, "
                 "Netzlaufwerke und verlinkte Ordner werden ausgelassen – verknüpfte Projekte: path=\"linked/<Name>\"."),
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Projekt (default: Workspace)",
            },
            "pattern": {
                "type": "string",
                "description": "Regex-Pattern das gesucht werden soll",
            },
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: Nur diese Dateiendungen (z.B. ['py', 'js'])",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Groß-/Kleinschreibung (default: true)",
            },
            "context": {
                "type": "integer",
                "description": "Anzahl Zeilen Kontext um jeden Treffer (default: 0)",
            },
            "max_results": {
                "type": "integer",
                "description": "Max Treffer gesamt (default: 100)",
            },
        },
        "required": ["pattern"],
    },
    execute=_execute,
)

"""grep — Durchsucht Dateien nach Regex-Pattern."""
import asyncio
import re
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult


EXCLUDED_DIRS = {"node_modules", "__pycache__", "venv", ".venv", "node_modules"}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    pattern = args.get("pattern", "")
    extensions = args.get("extensions", [])
    case_sensitive = args.get("case_sensitive", True)
    max_results = int(args.get("max_results", 100))
    context = int(args.get("context", 0))  # Lines around match
    
    if not pattern:
        return ToolResult.fail("Pattern ist erforderlich")
    
    root = Path(path_arg).resolve()
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    # Find files - handle extensions properly
    files = []
    if extensions:
        for ext in extensions:
            ext_clean = ext.strip(".")
            files.extend(root.glob(f"**/*.{ext_clean}"))
    else:
        files.extend(root.glob("**/*"))
    
    # Filter hidden dirs and non-files
    filtered_files = []
    for f in files:
        if not f.is_file():
            continue
        rel_parts = f.relative_to(root).parts
        if not any(part.startswith(".") or part in EXCLUDED_DIRS for part in rel_parts):
            filtered_files.append(f)
    files = list(set(filtered_files))  # Remove duplicates
    
    # Compile regex
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except Exception as e:
        return ToolResult.fail(f"Ungültiges Regex: {e}")
    
    # Search in files
    async def search_file(path: Path):
        try:
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
        "files_with_matches": len(files_with_matches),
        "total_matches": total_matches,
        "results_limited": total_matches >= max_results,
        "matches": files_with_matches[:20],  # Top 20 files
    })


TOOL = Tool(
    name="grep",
    description="Durchsucht Dateien nach Regex-Pattern. Gibt Datei, Zeile und Content zurück.",
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

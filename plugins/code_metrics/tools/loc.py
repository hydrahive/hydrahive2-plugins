"""loc — Zählt Lines of Code nach Dateityp."""
import asyncio
from pathlib import Path
from collections import defaultdict

from hydrahive.tools.base import Tool, ToolContext, ToolResult


# Sprach-Erkennung
EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".jsx": "JavaScript React",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".sql": "SQL",
    ".r": "R",
    ".lua": "Lua",
    ".pl": "Perl",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".ml": "OCaml",
    ".fs": "F#",
    ".clj": "Clojure",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


async def _count_file(path: Path) -> tuple[int, int, int]:
    """Zählt Zeilen in einer Datei. Returns (lines, code, comment)."""
    try:
        content = path.read_text(errors="ignore")
        lines = content.split("\n")
        total = len(lines)
        
        code = total
        comment = 0
        
        # Einfache Kommentar-Erkennung
        in_block = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                code -= 1
                continue
            
            # Block comments
            if stripped.startswith("'''") or stripped.startswith('"""'):
                in_block = not in_block
                code -= 1
                comment += 1
            elif in_block:
                comment += 1
                code -= 1
            # Single line comments
            elif stripped.startswith("#") or stripped.startswith("//"):
                comment += 1
                code -= 1
        
        return (total, max(0, code), max(0, comment))
    except Exception:
        return (0, 0, 0)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    pattern = args.get("pattern", "**/*")
    extensions = args.get("extensions", [])
    
    root = Path(path_arg).resolve()
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    # Build glob pattern
    if extensions:
        ext_patterns = "|".join(f"*.{e.strip('.')}" for e in extensions)
        glob_pattern = f"**/{{{ext_patterns}}}"
    else:
        glob_pattern = pattern
    
    # Find all files
    try:
        files = list(root.glob(glob_pattern))
    except Exception as e:
        return ToolResult.fail(f"Glob-Fehler: {e}")
    
    # Filter out hidden dirs, node_modules, __pycache__, etc.
    files = [f for f in files if f.is_file() and not any(
        part.startswith(".") or part in {"node_modules", "__pycache__", "venv", ".venv", "dist", "build", "target"}
        for part in f.relative_to(root).parts
    )]
    
    # Count lines concurrently
    results = await asyncio.gather(*[_count_file(f) for f in files])
    
    # Aggregate
    total_lines = 0
    total_code = 0
    total_comment = 0
    total_blank = 0
    
    for lines, code, comment in results:
        total_lines += lines
        total_code += code
        total_comment += comment
        total_blank += lines - code - comment
    
    return ToolResult.ok({
        "root": str(root),
        "pattern": glob_pattern,
        "total_files": len(files),
        "lines": {
            "total": total_lines,
            "code": total_code,
            "comment": total_comment,
            "blank": total_blank,
        },
        "languages": len(set(EXTENSIONS.get(f.suffix, "Other") for f in files)),
    })


TOOL = Tool(
    name="loc",
    description="Zählt Lines of Code nach Dateityp. Gibt Total, Code, Kommentare und Leerzeilen zurück.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Projekt (default: Workspace)",
            },
            "pattern": {
                "type": "string",
                "description": "Glob-Pattern für Dateien (default: **/*)",
            },
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: Nur diese Dateiendungen zählen (z.B. ['py', 'js'])",
            },
        },
        "required": [],
    },
    execute=_execute,
)

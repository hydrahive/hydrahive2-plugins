"""languages — Zeigt die Sprachen-Verteilung eines Projekts."""
import asyncio
from pathlib import Path
from collections import defaultdict

from hydrahive.tools.base import Tool, ToolContext, ToolResult


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
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".sh": "Shell",
    ".sql": "SQL",
}


async def _count_file(path: Path) -> tuple[str, int]:
    """Zählt Zeilen in einer Datei. Returns (language, lines)."""
    try:
        lines = len(path.read_text(errors="ignore").split("\n"))
        ext = path.suffix.lower()
        lang = EXTENSIONS.get(ext, "Other")
        return (lang, lines)
    except Exception:
        return ("Other", 0)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    
    root = Path(path_arg).resolve()
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    # Find all code files
    files = []
    for ext in EXTENSIONS.keys():
        files.extend(root.glob(f"**/*{ext}"))
    
    # Filter
    files = [f for f in set(files) if not any(
        part.startswith(".") or part in {"node_modules", "__pycache__", "venv", ".venv", "dist", "build", "target"}
        for part in f.relative_to(root).parts
    )]
    
    # Count by language
    results = await asyncio.gather(*[_count_file(f) for f in files])
    
    lang_stats: dict = defaultdict(lambda: {"files": 0, "lines": 0})
    for lang, lines in results:
        lang_stats[lang]["files"] += 1
        lang_stats[lang]["lines"] += lines
    
    total_lines = sum(s["lines"] for s in lang_stats.values())
    
    # Sort by lines
    sorted_langs = sorted(
        lang_stats.items(),
        key=lambda x: x[1]["lines"],
        reverse=True
    )
    
    languages = []
    for lang, stats in sorted_langs:
        pct = (stats["lines"] / total_lines * 100) if total_lines > 0 else 0
        languages.append({
            "language": lang,
            "files": stats["files"],
            "lines": stats["lines"],
            "percentage": round(pct, 1),
        })
    
    return ToolResult.ok({
        "root": str(root),
        "total_lines": total_lines,
        "total_files": len(files),
        "languages": languages,
    })


TOOL = Tool(
    name="languages",
    description="Zeigt die Sprachen-Verteilung eines Projekts mit Datei-Count und Prozent.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Projekt (default: Workspace)",
            },
        },
        "required": [],
    },
    execute=_execute,
)

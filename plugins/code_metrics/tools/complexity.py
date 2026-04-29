"""complexity — Schätzt Complexity/Quality-Indikatoren einer Codebase."""
import asyncio
import re
from pathlib import Path
from collections import defaultdict

from hydrahive.tools.base import Tool, ToolContext, ToolResult


# Code-Smell Patterns
COMPLEXITY_PATTERNS = {
    "long_function": {
        "pattern": re.compile(r"^\s*def\s+\w+\s*\([^)]*\)\s*:", re.MULTILINE),
        "name": "Function Definition",
    },
    "long_class": {
        "pattern": re.compile(r"^\s*class\s+\w+[^:]*:", re.MULTILINE),
        "name": "Class Definition",
    },
}

# Excluded directories
EXCLUDED_DIRS = {"node_modules", "__pycache__", "venv", ".venv", "dist", "build"}


async def _analyze_file(path: Path, max_lines: int = 200) -> dict:
    """Analysiert eine Datei auf Complexity-Indikatoren."""
    try:
        content = path.read_text(errors="ignore")
        lines = content.split("\n")
        line_count = len(lines)
        
        issues = []
        
        # Too long file?
        if line_count > max_lines:
            issues.append({
                "type": "long_file",
                "line": 0,
                "message": f"Datei hat {line_count} Zeilen (max: {max_lines})",
            })
        
        # Too long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 150:
                issues.append({
                    "type": "long_line",
                    "line": i,
                    "length": len(line),
                    "message": f"Zeile {i}: {len(line)} Zeichen",
                })
        
        # Deep nesting (tabs/spaces)
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped and not stripped.startswith("#"):
                indent = len(line) - len(stripped)
                if indent > 16:  # 4 levels of 4-space indent
                    issues.append({
                        "type": "deep_nesting",
                        "line": i,
                        "indent": indent,
                        "message": f"Zeile {i}: {indent} Spaces Einrückung",
                    })
        
        # TODO/FIXME comments
        todos = re.findall(r"(#.*(?:TODO|FIXME|HACK|XXX|BUG|NOTE):.*)", content, re.IGNORECASE)
        for todo in todos[:5]:  # Limit to 5
            issues.append({
                "type": "todo",
                "line": 0,
                "message": todo.strip()[:100],
            })
        
        return {
            "path": str(path),
            "lines": line_count,
            "issues": issues,
            "issue_count": len(issues),
        }
    except Exception as e:
        return {
            "path": str(path),
            "error": str(e),
            "lines": 0,
            "issues": [],
            "issue_count": 0,
        }


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    extensions = args.get("extensions", [".py"])
    max_lines = int(args.get("max_lines", 200))
    
    root = Path(path_arg).resolve()
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    # Find files
    files = []
    for ext in extensions:
        files.extend(root.glob(f"**/*{ext}"))
    
    # Filter excluded dirs
    filtered_files = []
    for f in files:
        rel_parts = f.relative_to(root).parts
        if not any(part.startswith(".") or part in EXCLUDED_DIRS for part in rel_parts):
            filtered_files.append(f)
    
    files = filtered_files[:100]
    
    # Analyze concurrently
    results = await asyncio.gather(*[_analyze_file(f, max_lines) for f in files])
    
    # Aggregate
    total_lines = sum(r["lines"] for r in results if "error" not in r)
    total_issues = sum(r["issue_count"] for r in results)
    
    issues_by_type: dict = defaultdict(list)
    for r in results:
        for issue in r["issues"]:
            issues_by_type[issue["type"]].append(issue)
    
    # Files with most issues
    problematic = sorted(results, key=lambda x: x["issue_count"], reverse=True)[:10]
    
    return ToolResult.ok({
        "root": str(root),
        "extensions": extensions,
        "files_analyzed": len(results),
        "total_lines": total_lines,
        "total_issues": total_issues,
        "issue_summary": {k: len(v) for k, v in issues_by_type.items()},
        "most_problematic": [
            {
                "path": r["path"],
                "issues": r["issue_count"],
                "lines": r["lines"],
            }
            for r in problematic
            if r["issue_count"] > 0
        ],
    })


TOOL = Tool(
    name="complexity",
    description="Analysiert Complexity-Indikatoren: lange Dateien, tiefe Einrückung, TODOs, etc.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Projekt (default: Workspace)",
            },
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dateitypen zu analysieren (default: ['.py'])",
            },
            "max_lines": {
                "type": "integer",
                "description": "Max Zeilen pro Datei bevor 'long_file' (default: 200)",
            },
        },
        "required": [],
    },
    execute=_execute,
)

"""tree — Zeigt Verzeichnis-Struktur als Baum."""
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    max_depth = int(args.get("max_depth", 3))
    show_files = args.get("show_files", True)
    extensions = args.get("extensions", [])
    exclude = args.get("exclude", [])
    
    root = Path(path_arg).resolve()
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    # Default exclusions
    exclude_defaults = {"node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build", "target", ".idea", ".vscode"}
    exclude.update(exclude_defaults)
    
    def build_tree(path: Path, prefix: str = "", depth: int = 0) -> list[str]:
        """Rekursiv Verzeichnisbaum bauen."""
        if depth >= max_depth:
            return []
        
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return []
        
        lines = []
        dirs = []
        files = []
        
        for item in items:
            name = item.name
            if name.startswith(".") and name not in {".gitignore", ".env"}:
                continue
            if name in exclude:
                continue
            
            if item.is_dir():
                dirs.append(item)
            elif show_files:
                # Extension filter
                if extensions and item.suffix not in [f".{e.strip('.')}" for e in extensions]:
                    continue
                files.append(item)
        
        # Draw dirs
        for i, d in enumerate(dirs):
            is_last = (i == len(dirs) - 1) and len(files) == 0
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{d.name}/")
            
            ext = "    " if is_last else "│   "
            lines.extend(build_tree(d, prefix + ext, depth + 1))
        
        # Draw files
        for i, f in enumerate(files):
            is_last = i == len(files) - 1
            connector = "└── " if is_last else "├── "
            size = f.stat().st_size
            size_str = _format_size(size) if size < 1024*100 else f"({_format_size(size)})"
            lines.append(f"{prefix}{connector}{f.name} {size_str}")
        
        return lines
    
    tree_lines = build_tree(root)
    
    # Stats
    total_files = sum(1 for _ in root.rglob("*") if _.is_file() and not any(
        p.startswith(".") or p in exclude_defaults for p in _.relative_to(root).parts
    ))
    total_dirs = sum(1 for _ in root.rglob("*") if _.is_dir() and not any(
        p.startswith(".") or p in exclude_defaults for p in _.relative_to(root).parts
    ))
    
    return ToolResult.ok({
        "path": str(root),
        "max_depth": max_depth,
        "total_files": total_files,
        "total_dirs": total_dirs,
        "tree": "\n".join(tree_lines) if tree_lines else "(leer)",
    })


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024*1024:
        return f"{size//1024}KB"
    else:
        return f"{size//1024//1024}MB"


TOOL = Tool(
    name="tree",
    description="Zeigt Verzeichnis-Struktur als Baum mit Größen.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Verzeichnis (default: Workspace)",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximale Tiefe (default: 3)",
            },
            "show_files": {
                "type": "boolean",
                "description": "Dateien anzeigen (default: true)",
            },
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: Nur diese Endungen",
            },
            "exclude": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Verzeichnisse auszuschließen",
            },
        },
        "required": [],
    },
    execute=_execute,
)

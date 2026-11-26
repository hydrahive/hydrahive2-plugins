"""tree — Zeigt Verzeichnis-Struktur als Baum."""
import asyncio
import os
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


EXCLUDED_DEFAULTS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build", "target", ".idea", ".vscode"}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path_arg = args.get("path", str(ctx.workspace))
    max_depth = int(args.get("max_depth", 3))
    show_files = args.get("show_files", True)
    extensions = args.get("extensions", [])
    exclude_list = args.get("exclude", [])
    
    # Convert to set
    exclude = set(exclude_list) if exclude_list else set()
    exclude.update(EXCLUDED_DEFAULTS)
    
    try:
    
        root = read_path(ctx, path_arg)
    
    except PathOutsideWorkspace as e:
    
        return ToolResult.fail(str(e))
    if not root.exists():
        return ToolResult.fail(f"Pfad existiert nicht: {root}")
    
    root_dev = root.stat().st_dev

    def build_tree(path: Path, prefix: str = "", depth: int = 0) -> list:
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
                # Keine Symlink-Ordner, keine anderen Dateisysteme (Netzlaufwerke) – nur als Name zeigen.
                try:
                    if os.path.islink(item) or item.lstat().st_dev != root_dev:
                        files.append(item) if show_files else None
                        continue
                except OSError:
                    continue
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
            try:
                if f.is_dir():
                    lines.append(f"{prefix}{connector}{f.name}/ (Mount/Verweis, nicht betreten)")
                    continue
                size = f.stat().st_size
            except OSError:
                continue
            size_str = _format_size(size) if size < 1024*100 else f"({_format_size(size)})"
            lines.append(f"{prefix}{connector}{f.name} {size_str}")
        
        return lines
    
    # Baum und Zählung im Worker-Thread (vorher rglob über ALLES synchron im Event-Loop, auch Netzlaufwerke).
    tree_lines = await asyncio.to_thread(build_tree, root)
    walked = await asyncio.to_thread(_walk.walk, root, max_depth=50, extra_skip=exclude - _walk.SKIP_DIRS)

    out = {
        "path": str(root),
        "max_depth": max_depth,
        "total_files": len(walked.files),
        "total_dirs": walked.dirs,
        "tree": "\n".join(tree_lines) if tree_lines else "(leer)",
    }
    if walked.stopped:
        out["counts_incomplete"] = f"{walked.stopped} erreicht – Zählung unvollständig"
    if walked.skipped_mounts or walked.skipped_links:
        out["not_entered"] = (walked.skipped_mounts + walked.skipped_links)[:10]
    return ToolResult.ok(out)


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024*1024:
        return f"{size//1024}KB"
    else:
        return f"{size//1024//1024}MB"


TOOL = Tool(
    name="tree",
    description=("Zeigt Verzeichnis-Struktur als Baum mit Größen. Netzlaufwerke und verlinkte Ordner nur als Name – "
                 "verknüpfte Projekte direkt anzeigen: path=\"linked/<Name>\"."),
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

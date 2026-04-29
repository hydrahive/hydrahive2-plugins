"""git_files — Zeigt Dateien mit Änderungsstatistik eines Git-Repos."""
import asyncio
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path = args.get("path", str(ctx.workspace))
    pattern = args.get("pattern", "")
    
    repo = Path(path).resolve()
    if not (repo / ".git").exists():
        return ToolResult.fail(f"Kein Git-Repo gefunden in: {repo}")
    
    # Get stats with --numstat for machine-readable output
    cmd = [
        "git", "-C", str(repo),
        "log", "--oneline", "--all",
        "--numstat",
        "--format="
    ]
    
    if pattern:
        cmd.append(f"-- {pattern}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return ToolResult.fail(f"Git-Fehler: {stderr.decode()}")
        
        # Aggregate stats per file
        stats: dict = {}
        lines = stdout.decode().strip().split("\n")
        
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                added = int(parts[0]) if parts[0] != "-" else 0
                deleted = int(parts[1]) if parts[1] != "-" else 0
                filename = parts[2]
                
                if filename not in stats:
                    stats[filename] = {"added": 0, "deleted": 0, "changes": 0}
                stats[filename]["added"] += added
                stats[filename]["deleted"] += deleted
                stats[filename]["changes"] += 1
        
        # Convert to sorted list
        files = sorted(
            [{"file": k, **v} for k, v in stats.items()],
            key=lambda x: x["changes"],
            reverse=True
        )[:50]  # Top 50
        
        total_added = sum(f["added"] for f in files)
        total_deleted = sum(f["deleted"] for f in files)
        
        return ToolResult.ok({
            "repo": str(repo),
            "filter": pattern or None,
            "total_files": len(stats),
            "shown_files": len(files),
            "total_added": total_added,
            "total_deleted": total_deleted,
            "files": files,
        })
    except Exception as e:
        return ToolResult.fail(f"Fehler: {e}")


TOOL = Tool(
    name="git_files",
    description="Zeigt Dateien mit Änderungsstatistik (Lines Added/Deleted, Change-Count).",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Git-Repo (default: aktueller Workspace)",
            },
            "pattern": {
                "type": "string",
                "description": "Optional: Nur Dateien die diesem Pfad-Muster entsprechen",
            },
        },
        "required": [],
    },
    execute=_execute,
)

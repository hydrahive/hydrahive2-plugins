"""git_commits — Zeigt die letzten N Commits einer Git-Repo."""
import asyncio
import json
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path = args.get("path", str(ctx.workspace))
    limit = min(int(args.get("limit", 10)), 100)
    
    repo = Path(path).resolve()
    if not (repo / ".git").exists():
        return ToolResult.fail(f"Kein Git-Repo gefunden in: {repo}")
    
    cmd = [
        "git", "-C", str(repo),
        "log", "--oneline", "--decorate",
        f"-{limit}",
        "--pretty=format:%h|%s|%an|%ad",
        "--date=short"
    ]
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return ToolResult.fail(f"Git-Fehler: {stderr.decode()}")
        
        lines = stdout.decode().strip().split("\n")
        commits = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                })
            elif len(parts) == 3:
                commits.append({
                    "hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "date": "?",
                })
        
        return ToolResult.ok({
            "repo": str(repo),
            "count": len(commits),
            "commits": commits,
        })
    except Exception as e:
        return ToolResult.fail(f"Fehler: {e}")


TOOL = Tool(
    name="git_commits",
    description="Zeigt die letzten N Commits eines Git-Repos. Gibt Hash, Message, Author und Datum zurück.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Git-Repo (default: aktueller Workspace)",
            },
            "limit": {
                "type": "integer",
                "description": "Anzahl Commits (default: 10, max: 100)",
                "default": 10,
            },
        },
        "required": [],
    },
    execute=_execute,
)

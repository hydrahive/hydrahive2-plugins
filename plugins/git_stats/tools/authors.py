"""git_authors — Zeigt alle Autoren mit Commit-Count eines Git-Repos."""
import asyncio
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path = args.get("path", str(ctx.workspace))
    
    repo = Path(path).resolve()
    if not (repo / ".git").exists():
        return ToolResult.fail(f"Kein Git-Repo gefunden in: {repo}")
    
    cmd = [
        "git", "-C", str(repo),
        "shortlog", "--all", "--no-merges",
        "-sne", "--format=%an|%ae"
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
        authors = []
        total = 0
        
        for line in lines:
            if not line.strip():
                continue
            # Format: "   123  Name <email@domain>"
            parts = line.strip().split(None, 1)
            if len(parts) >= 2:
                count = int(parts[0])
                rest = parts[1]
                name_email = rest.rsplit("<", 1)
                if len(name_email) == 2:
                    name = name_email[0].strip().rstrip("-")
                    email = f"<{name_email[1]}"
                    authors.append({
                        "name": name,
                        "email": email,
                        "commits": count,
                    })
                    total += count
        
        # Sort by commits descending
        authors.sort(key=lambda x: x["commits"], reverse=True)
        
        return ToolResult.ok({
            "repo": str(repo),
            "total_commits": total,
            "author_count": len(authors),
            "authors": authors,
        })
    except Exception as e:
        return ToolResult.fail(f"Fehler: {e}")


TOOL = Tool(
    name="git_authors",
    description="Zeigt alle Autoren eines Git-Repos mit Commit-Count, sortiert nach Aktivität.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Git-Repo (default: aktueller Workspace)",
            },
        },
        "required": [],
    },
    execute=_execute,
)

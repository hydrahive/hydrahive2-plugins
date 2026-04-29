"""git_diff — Zeigt Diff zwischen Commits oder Branches."""
import asyncio
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    path = args.get("path", str(ctx.workspace))
    ref = args.get("ref", "HEAD")
    file_filter = args.get("file", "")
    
    repo = Path(path).resolve()
    if not (repo / ".git").exists():
        return ToolResult.fail(f"Kein Git-Repo gefunden in: {repo}")
    
    # Get diff against ref or between two refs
    ref2 = args.get("ref2", "")
    
    cmd = [
        "git", "-C", str(repo),
        "diff", "--no-color",
    ]
    
    if ref2:
        cmd.extend([ref, ref2])
    else:
        cmd.append(ref)
    
    if file_filter:
        cmd.append("--")
        cmd.append(file_filter)
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return ToolResult.fail(f"Git-Fehler: {stderr.decode()}")
        
        diff = stdout.decode()
        
        # Parse diff stats
        stat_cmd = ["git", "-C", str(repo), "diff", "--stat", "--no-color"]
        if ref2:
            stat_cmd.extend([ref, ref2])
        else:
            stat_cmd.append(ref)
        if file_filter:
            stat_cmd.extend(["--", file_filter])
        
        stat_proc = await asyncio.create_subprocess_exec(
            *stat_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stat_stdout, _ = await stat_proc.communicate()
        stat = stat_stdout.decode().strip()
        
        return ToolResult.ok({
            "repo": str(repo),
            "ref": ref,
            "ref2": ref2 or None,
            "file": file_filter or None,
            "stat": stat,
            "diff": diff if diff else "(keine Änderungen)",
        })
    except Exception as e:
        return ToolResult.fail(f"Fehler: {e}")


TOOL = Tool(
    name="git_diff",
    description="Zeigt Diff zwischen zwei Commits/Branches oder Changes eines einzelnen Commits.",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad zum Git-Repo (default: aktueller Workspace)",
            },
            "ref": {
                "type": "string",
                "description": "Erster Commit/Branch (default: HEAD)",
                "default": "HEAD",
            },
            "ref2": {
                "type": "string",
                "description": "Zweiter Commit/Branch für Vergleich (optional)",
            },
            "file": {
                "type": "string",
                "description": "Optional: Nur diese Datei anzeigen",
            },
        },
        "required": [],
    },
    execute=_execute,
)

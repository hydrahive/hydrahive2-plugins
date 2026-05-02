"""video — Generiert Videos mit MiniMax AI via mmx-CLI (synchron)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")

    out_dir = ctx.workspace / "media" / "videos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    cmd = ["mmx", "--non-interactive", "video", "generate",
           "--prompt", prompt, "--download", str(out_path)]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout (600s) bei Video-Generierung — mmx ist evtl. noch dabei")

    err = stderr.decode().strip()
    if proc.returncode != 0:
        return ToolResult.fail(f"mmx exit={proc.returncode}: {err or stdout.decode()[:200]}")

    if not out_path.exists() or out_path.stat().st_size < 10_000:
        return ToolResult.fail(f"Video-Datei fehlt/zu klein. stderr: {err[:200]}")

    return ToolResult.ok({"output_file": str(out_path), "prompt": prompt})


_DESC = (
    "Generiert ein Video mit MiniMax AI (Hailuo, ~10s, kann 1-5 Min "
    "dauern) und gibt den absoluten MP4-Pfad zurück. Speichert in den "
    "Workspace unter media/videos/. Das Frontend rendert den Video-Player "
    "automatisch aus dem Tool-Result."
)

TOOL = Tool(
    name="video",
    description=_DESC,
    schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Szenenbeschreibung"},
        },
        "required": ["prompt"],
    },
    execute=_execute,
)

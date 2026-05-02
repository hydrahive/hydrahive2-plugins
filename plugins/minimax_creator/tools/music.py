"""music — Generiert Musik mit MiniMax AI via mmx-CLI."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

OUT_DIR = Path("/tmp/mmx_music")


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = (args.get("prompt") or "").strip()
    lyrics = (args.get("lyrics") or "").strip()
    instrumental = bool(args.get("instrumental"))
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"music_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

    cmd = ["mmx", "--non-interactive", "music", "generate",
           "--prompt", prompt, "--out", str(out_path)]
    if lyrics:
        cmd += ["--lyrics", lyrics]
    elif instrumental:
        cmd += ["--instrumental"]
    else:
        cmd += ["--lyrics-optimizer"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout (300s) bei Musik-Generierung")

    err = stderr.decode().strip()
    if proc.returncode != 0:
        return ToolResult.fail(f"mmx exit={proc.returncode}: {err or stdout.decode()[:200]}")

    if not out_path.exists() or out_path.stat().st_size < 1000:
        return ToolResult.fail(f"Musik-Datei fehlt oder zu klein. stderr: {err[:200]}")

    return ToolResult.ok({"output_file": str(out_path), "prompt": prompt,
                           "instrumental": instrumental})


_DESC = (
    "Generiert ein Musikstück mit MiniMax AI und gibt den absoluten Pfad "
    "zur MP3 zurück. Speichert nach /tmp/mmx_music/. Das Frontend rendert "
    "den Audio-Player automatisch aus dem Tool-Result — du musst NICHTS "
    "extra tun. Antworte dem User einfach kurz dass die Musik da ist."
)

TOOL = Tool(
    name="music",
    description=_DESC,
    schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string",
                       "description": "Musik-Stil (z.B. 'cinematic orchestral, building tension')"},
            "lyrics": {"type": "string",
                       "description": "Optional: Songtext mit [Verse]/[Chorus]-Tags"},
            "instrumental": {"type": "boolean",
                             "description": "Wenn true: ohne Gesang"},
        },
        "required": ["prompt"],
    },
    execute=_execute,
)

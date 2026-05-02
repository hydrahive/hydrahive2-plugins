"""image — Generiert Bilder mit MiniMax AI via mmx-CLI."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = (args.get("prompt") or "").strip()
    aspect = args.get("aspect_ratio") or "1:1"
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")

    out_dir = ctx.workspace / "media" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    cmd = [
        "mmx", "--output", "json", "--non-interactive",
        "image", "generate",
        "--prompt", prompt,
        "--aspect-ratio", aspect,
        "--out-dir", str(out_dir),
        "--out-prefix", prefix,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout (180s) bei Bild-Generierung")

    out = stdout.decode().strip()
    err = stderr.decode().strip()
    if proc.returncode != 0:
        return ToolResult.fail(f"mmx exit={proc.returncode}: {err or out}")

    try:
        data = json.loads(out)
        saved = data.get("saved") or []
    except json.JSONDecodeError:
        return ToolResult.fail(f"mmx-Output kein JSON: {out[:200]}")

    if not saved:
        return ToolResult.fail(f"mmx hat keine Datei gespeichert. stderr: {err[:200]}")

    from pathlib import Path
    path = saved[0] if Path(saved[0]).is_absolute() else str(out_dir / saved[0])
    return ToolResult.ok({"output_file": path, "all_files": saved, "prompt": prompt})


_DESC = (
    "Generiert ein Bild mit MiniMax AI und gibt den absoluten Dateipfad "
    "zurück. Speichert in den Workspace unter media/images/. Das Frontend "
    "rendert das Bild automatisch aus dem Tool-Result. Antworte dem User "
    "einfach kurz dass das Bild da ist."
)

TOOL = Tool(
    name="image",
    description=_DESC,
    schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Bildbeschreibung"},
            "aspect_ratio": {
                "type": "string", "enum": ["1:1", "16:9", "9:16", "4:3", "3:4"],
                "description": "Seitenverhältnis (default 1:1)",
            },
        },
        "required": ["prompt"],
    },
    execute=_execute,
)

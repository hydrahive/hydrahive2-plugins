"""speech — Text-to-Speech mit MiniMax AI via mmx-CLI."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    text = (args.get("text") or "").strip()
    voice = args.get("voice") or ""
    speed = args.get("speed")
    if not text:
        return ToolResult.fail("text ist erforderlich")

    # Daily-Cap (deterministisch, gemeinsam mit /api/tts).
    try:
        from hydrahive.voice import _quota as tts_quota
        allowed, used, cap = tts_quota.check_and_increment(ctx.user_id)
        if not allowed:
            return ToolResult.fail(
                f"TTS-Tageslimit erreicht ({used}/{cap}). Reset um Mitternacht UTC."
            )
    except Exception as exc:
        logger.warning("Quota-Check fehlgeschlagen, lasse durch: %s", exc)

    out_dir = ctx.workspace / "media" / "speech"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

    cmd = ["mmx", "--non-interactive", "speech", "synthesize",
           "--text", text, "--out", str(out_path)]
    if voice:
        cmd += ["--voice", voice]
    if speed is not None:
        cmd += ["--speed", str(speed)]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout (120s) bei Speech-Synthese")

    err = stderr.decode().strip()
    if proc.returncode != 0:
        return ToolResult.fail(f"mmx exit={proc.returncode}: {err or stdout.decode()[:200]}")

    if not out_path.exists() or out_path.stat().st_size < 500:
        return ToolResult.fail(f"Audio-Datei fehlt/zu klein. stderr: {err[:200]}")

    return ToolResult.ok({"output_file": str(out_path), "text_preview": text[:80]})


_DESC = (
    "Text-to-Speech mit MiniMax AI — gibt den absoluten Pfad zur MP3 "
    "zurück. Speichert in den Workspace unter media/speech/. Das Frontend "
    "rendert den Audio-Player automatisch aus dem Tool-Result."
)

TOOL = Tool(
    name="speech",
    description=_DESC,
    schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text zum Sprechen"},
            "voice": {"type": "string",
                      "description": "Optional: Voice-ID (default English_expressive_narrator)"},
            "speed": {"type": "number", "description": "0.5 - 2.0, default 1.0"},
        },
        "required": ["text"],
    },
    execute=_execute,
)

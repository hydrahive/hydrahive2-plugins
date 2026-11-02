"""music — derzeit NICHT NUTZBAR (Befund 02.11.2026), meldet den Ausfall klar.

Zwei Gründe, live geprüft:
1. Die mmx-CLI hat KEIN "music"-Kommando. `mmx --help` listet
   auth/text/speech/image/video/search/vision/quota/config/agent/file/update.
   Ein Aufruf von "mmx music generate" endet mit:
       Unknown command: mmx music generate   (exit=2)
2. Die MiniMax-Musik-API ist für Neukunden abgeschaltet. Ein direkter Aufruf von
   /v1/music_generation antwortet:
       "This Music API is no longer available to new users. Existing paying
        customers can continue to use the service."

Der funktionierende Weg für Musik ist das Kern-Werkzeug `generate_music`
(OpenRouter/Lyria: google/lyria-3-pro-preview für ganze Stücke,
google/lyria-3-clip-preview für kurze Clips).

Statt eines irreführenden API-Fehlers sagt dieses Werkzeug klar, was los ist
und wohin es geht. Sobald eine mmx-Version Musik wieder freigibt, wird der
Aufruf unten (er liegt als Kommentar bereit) wieder aktiviert.
"""
from __future__ import annotations

import logging

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from ._mmx import minimax_api_key, mmx_binary, missing_key_message

logger = logging.getLogger(__name__)

_UNAVAILABLE = (
    "MiniMax-Musik ist derzeit nicht verfügbar: die mmx-CLI hat kein "
    "'music'-Kommando und die MiniMax-Musik-API ist für Neukunden "
    "abgeschaltet. Nutze stattdessen das Kern-Werkzeug 'generate_music' "
    "(OpenRouter/Lyria) – das erzeugt ganze Stücke."
)

# Für eine spätere mmx-Version mit Musik-Unterstützung:
#
#   cmd = [*mmx_base_cmd(api_key), "music", "generate",
#          "--prompt", prompt, "--out", str(out_path)]
#   if lyrics:
#       cmd += ["--lyrics", lyrics]
#   elif instrumental:
#       cmd += ["--instrumental"]
#   else:
#       cmd += ["--lyrics-optimizer"]


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")

    if not mmx_binary():
        return ToolResult.fail("mmx-CLI fehlt (npm install -g mmx-cli)")

    if not minimax_api_key():
        return ToolResult.fail(missing_key_message())

    return ToolResult.fail(_UNAVAILABLE)


_DESC = (
    "Nicht verfügbar: MiniMax-Musik wird aktuell nicht unterstützt (die mmx-CLI "
    "hat kein 'music'-Kommando, die MiniMax-Musik-API ist für Neukunden "
    "abgeschaltet). Für Musik bitte das Kern-Werkzeug 'generate_music' nutzen "
    "(OpenRouter/Lyria). Dieses Werkzeug meldet nur den Ausfall."
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

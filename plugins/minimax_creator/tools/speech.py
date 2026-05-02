"""speech — Text-to-Speech mit MiniMax AI."""
import asyncio
import json
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult


def _get_output_dir():
    from pathlib import Path
    d = Path("/tmp/mmx_speech")
    d.mkdir(exist_ok=True)
    return d


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    text = args.get("text", "")
    voice = args.get("voice", None)
    speed = args.get("speed", 1.0)
    output = args.get("output", None)
    
    if not text:
        return ToolResult.fail("text ist erforderlich")
    
    if output:
        filename = output
    else:
        out_dir = _get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = str(out_dir / f"mmx_speech_{timestamp}.mp3")
    
    cmd = ["mmx", "speech", "synthesize", "--text", text, "--output", filename]
    if voice:
        cmd.extend(["--voice", voice])
    if speed != 1.0:
        cmd.extend(["--speed", str(speed)])
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        
        try:
            data = json.loads(stdout.decode())
            if data.get("base_resp", {}).get("status_code") == 0:
                return ToolResult.ok({
                    "success": True,
                    "text": text[:100],
                    "voice": voice or "default",
                    "output_file": filename,
                })
            else:
                return ToolResult.fail(f"MiniMax Error: {stdout.decode()}")
        except json.JSONDecodeError:
            return ToolResult.fail(f"Keine gültige JSON-Antwort: {stdout.decode()[:200]}")
            
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout nach 60s — Speech-Synthese zu langsam")
    except Exception as e:
        return ToolResult.fail(f"Speech-Synthese fehlgeschlagen: {str(e)}")


_DESC = (
    "Text-to-Speech mit MiniMax AI — speichert das Ergebnis als MP3-Datei. "
    "WICHTIG: Nach Erfolg MUSST du den absoluten Pfad aus `output_file` "
    "wortwörtlich in deine Antwort an den User schreiben — die Chat-UI "
    "rendert Audio-Player nur dann, wenn der absolute Pfad (z.B. "
    "/tmp/mmx_speech/mmx_speech_20260502_092000.mp3) im Antwort-Text "
    "vorkommt. Erfinde KEINE Pfade. Lies den Wert aus dem Tool-Result."
)

TOOL = Tool(
    name="speech",
    description=_DESC,
    schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text der gesprochen werden soll"},
            "voice": {"type": "string", "description": "Stimme (optional)"},
            "speed": {"type": "number", "description": "Geschwindigkeit 0.5-2.0"},
        },
        "required": ["text"],
    },
    execute=_execute,
)

"""music — Generiert Musik mit MiniMax AI."""
import asyncio
import json
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult


def _get_output_dir():
    from pathlib import Path
    d = Path("/tmp/mmx_music")
    d.mkdir(exist_ok=True)
    return d


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = args.get("prompt", "")
    title = args.get("title", None)
    output = args.get("output", None)
    
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")
    
    if output:
        filename = output
    else:
        out_dir = _get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = str(out_dir / f"mmx_music_{timestamp}.mp3")
    
    cmd = ["mmx", "music", "generate", "--prompt", prompt, "--output", filename]
    if title:
        cmd.extend(["--title", title])
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        
        try:
            data = json.loads(stdout.decode())
            if data.get("base_resp", {}).get("status_code") == 0:
                return ToolResult.ok({
                    "success": True,
                    "prompt": prompt,
                    "title": title or "Unnamed",
                    "output_file": filename,
                })
            else:
                return ToolResult.fail(f"MiniMax Error: {stdout.decode()}")
        except json.JSONDecodeError:
            return ToolResult.fail(f"Keine gültige JSON-Antwort: {stdout.decode()[:200]}")
            
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout nach 180s — Musik-Generierung zu langsam")
    except Exception as e:
        return ToolResult.fail(f"Musik-Generierung fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="music",
    description="Generiert Musik mit MiniMax AI.",
    schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Musik-Beschreibung"},
            "title": {"type": "string", "description": "Optional: Titel"},
        },
        "required": ["prompt"],
    },
    execute=_execute,
)

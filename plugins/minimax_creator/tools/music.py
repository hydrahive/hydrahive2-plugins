"""music — Generiert Musik mit MiniMax AI."""
import asyncio
import subprocess
import json
from pathlib import Path
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult


OUTPUT_DIR = Path("/tmp/mmx_music")
OUTPUT_DIR.mkdir(exist_ok=True)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = args.get("prompt", "")
    title = args.get("title", None)
    output = args.get("output", None)
    
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output or f"mmx_music_{timestamp}.mp3"
    
    # Build command
    cmd = ["mmx", "music", "generate", "--prompt", prompt]
    if title:
        cmd.extend(["--title", title])
    cmd.extend(["--output", filename])
    
    try:
        # Run mmx
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        result = stdout.decode() + stderr.decode()
        
        # Parse JSON output
        try:
            data = json.loads(result)
            if data.get("base_resp", {}).get("status_code") == 0:
                return ToolResult.ok({
                    "success": True,
                    "prompt": prompt,
                    "title": title or "Unnamed",
                    "output_file": filename,
                    "message": "Musik erfolgreich generiert!",
                })
            else:
                return ToolResult.fail(f"MiniMax Error: {result}")
        except json.JSONDecodeError:
            return ToolResult.ok({
                "success": True,
                "prompt": prompt,
                "output": result,
            })
            
    except Exception as e:
        return ToolResult.fail(f"Musik-Generierung fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="music",
    description="Generiert Musik mit MiniMax AI. Beschreibe die Musik die du willst.",
    schema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Beschreibung der Musik (Genre, Stimmung, Instrumente)",
            },
            "title": {
                "type": "string",
                "description": "Optional: Titel für das Musikstück",
            },
            "output": {
                "type": "string",
                "description": "Optional: Ausgabedatei-Pfad",
            },
        },
        "required": ["prompt"],
    },
    execute=_execute,
)

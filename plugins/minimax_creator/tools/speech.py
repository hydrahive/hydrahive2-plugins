"""speech — Text-to-Speech mit MiniMax AI."""
import asyncio
import subprocess
import json
from pathlib import Path
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult


OUTPUT_DIR = Path("/tmp/mmx_speech")
OUTPUT_DIR.mkdir(exist_ok=True)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    text = args.get("text", "")
    voice = args.get("voice", "female-young")  # voice ID
    speed = args.get("speed", 1.0)
    output = args.get("output", None)
    
    if not text:
        return ToolResult.fail("text ist erforderlich")
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output or f"mmx_speech_{timestamp}.mp3"
    
    # Build command
    cmd = ["mmx", "speech", "synthesize", "--text", text]
    if voice:
        cmd.extend(["--voice", voice])
    if speed != 1.0:
        cmd.extend(["--speed", str(speed)])
    cmd.extend(["--output", filename])
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        result = stdout.decode() + stderr.decode()
        
        try:
            data = json.loads(result)
            if data.get("base_resp", {}).get("status_code") == 0:
                return ToolResult.ok({
                    "success": True,
                    "text": text[:100],
                    "voice": voice,
                    "speed": speed,
                    "output_file": filename,
                    "message": "Sprache erfolgreich generiert!",
                })
        except json.JSONDecodeError:
            pass
        
        return ToolResult.ok({
            "success": True,
            "text": text[:100],
            "voice": voice,
            "output": result[:500],
        })
            
    except Exception as e:
        return ToolResult.fail(f"Speech-Synthese fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="speech",
    description="Text-to-Speech mit MiniMax AI. Wandelt Text in Sprache um.",
    schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text der gesprochen werden soll",
            },
            "voice": {
                "type": "string",
                "description": "Stimme (default: female-young)",
            },
            "speed": {
                "type": "number",
                "description": "Geschwindigkeit 0.5-2.0 (default: 1.0)",
            },
            "output": {
                "type": "string",
                "description": "Optional: Ausgabedatei-Pfad",
            },
        },
        "required": ["text"],
    },
    execute=_execute,
)

"""vision — Bildanalyse mit MiniMax AI."""
import asyncio
import subprocess
import json

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    image = args.get("image", "")
    prompt = args.get("prompt", "Beschreibe was auf dem Bild zu sehen ist")
    
    if not image:
        return ToolResult.fail("image ist erforderlich (Dateipfad oder URL)")
    
    # Build command
    cmd = ["mmx", "vision", "describe", "--image", image]
    if prompt != "Beschreibe was auf dem Bild zu sehen ist":
        cmd.extend(["--prompt", prompt])
    
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
            description = data.get("content", "")
            if description:
                return ToolResult.ok({
                    "success": True,
                    "image": image,
                    "description": description,
                    "raw_response": data,
                })
        except json.JSONDecodeError:
            pass
        
        return ToolResult.ok({
            "success": True,
            "image": image,
            "description": result,
        })
            
    except Exception as e:
        return ToolResult.fail(f"Bild-Analyse fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="vision",
    description="Analysiert ein Bild mit MiniMax Vision. Gibt Beschreibung zurück.",
    schema={
        "type": "object",
        "properties": {
            "image": {
                "type": "string",
                "description": "Bild-Pfad oder URL",
            },
            "prompt": {
                "type": "string",
                "description": "Optional: Spezielle Frage zum Bild",
            },
        },
        "required": ["image"],
    },
    execute=_execute,
)

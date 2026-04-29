"""image — Generiert Bilder mit MiniMax AI."""
import asyncio
import subprocess
import json
from pathlib import Path
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult


OUTPUT_DIR = Path("/tmp/mmx_images")
OUTPUT_DIR.mkdir(exist_ok=True)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = args.get("prompt", "")
    size = args.get("size", "1:1")  # 1:1, 16:9, 9:16, 4:3
    style = args.get("style", "natural")  # natural, anime, realistic
    output = args.get("output", None)  # Optional custom path
    
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")
    
    # Parse size
    size_map = {
        "1:1": "1:1",
        "16:9": "16:9",
        "9:16": "9:16",
        "4:3": "4:3",
    }
    size_arg = size_map.get(size, "1:1")
    
    # Style argument
    style_arg = "--style" if style == "anime" else None
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output or f"mmx_image_{timestamp}.jpg"
    
    # Build command
    cmd = ["mmx", "image", "generate", "--prompt", prompt, "--aspect", size_arg]
    if style_arg:
        cmd.append(style_arg)
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
                    "size": size_arg,
                    "style": style,
                    "output_file": filename,
                    "message": "Bild erfolgreich generiert!",
                })
            else:
                return ToolResult.fail(f"MiniMax Error: {result}")
        except json.JSONDecodeError:
            return ToolResult.ok({
                "success": True,
                "prompt": prompt,
                "output": result,
                "raw_output": result[:500],
            })
            
    except Exception as e:
        return ToolResult.fail(f"Bild-Generierung fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="image",
    description="Generiert Bilder mit MiniMax AI. Gibt einen Prompt ein und erhalte ein Bild.",
    schema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Beschreibung des zu generierenden Bildes",
            },
            "size": {
                "type": "string",
                "enum": ["1:1", "16:9", "9:16", "4:3"],
                "description": "Seitenverhältnis (default: 1:1)",
            },
            "style": {
                "type": "string",
                "enum": ["natural", "anime", "realistic"],
                "description": "Bildstil (default: natural)",
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

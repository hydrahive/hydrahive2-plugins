"""image — Generiert Bilder mit MiniMax AI."""
import asyncio
import json
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult


def _get_output_dir():
    """Lazily create output directory only when needed."""
    from pathlib import Path
    d = Path("/tmp/mmx_images")
    d.mkdir(exist_ok=True)
    return d


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = args.get("prompt", "")
    size = args.get("size", "1:1")
    output = args.get("output", None)
    
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")
    
    size_map = {"1:1": "1:1", "16:9": "16:9", "9:16": "9:16", "4:3": "4:3"}
    size_arg = size_map.get(size, "1:1")
    
    if output:
        filename = output
    else:
        out_dir = _get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = str(out_dir / f"mmx_image_{timestamp}.jpg")
    
    cmd = ["mmx", "image", "generate", "--prompt", prompt, "--aspect", size_arg, "--output", filename]
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        
        # Nur stdout parsen (JSON kommt über stdout)
        try:
            data = json.loads(stdout.decode())
            if data.get("base_resp", {}).get("status_code") == 0:
                return ToolResult.ok({
                    "success": True,
                    "prompt": prompt,
                    "size": size_arg,
                    "output_file": filename,
                })
            else:
                return ToolResult.fail(f"MiniMax Error: {stdout.decode()}")
        except json.JSONDecodeError:
            return ToolResult.fail(f"Keine gültige JSON-Antwort: {stdout.decode()[:200]}")
            
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout nach 120s — Bild-Generierung zu langsam")
    except Exception as e:
        return ToolResult.fail(f"Bild-Generierung fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="image",
    description="Generiert Bilder mit MiniMax AI.",
    schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Beschreibung des Bildes"},
            "size": {"type": "string", "enum": ["1:1", "16:9", "9:16", "4:3"], "description": "Seitenverhältnis"},
        },
        "required": ["prompt"],
    },
    execute=_execute,
)

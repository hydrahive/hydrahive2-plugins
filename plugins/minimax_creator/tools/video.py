"""video — Generiert Videos mit MiniMax AI."""
import asyncio
import json
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = args.get("prompt", "")
    duration = args.get("duration", 5)
    output = args.get("output", None)
    
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")
    
    if output:
        filename = output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/tmp/mmx_video_{timestamp}.mp4"
    
    cmd = ["mmx", "video", "generate", "--prompt", prompt, "--output", filename]
    if duration:
        cmd.extend(["--duration", str(duration)])
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        
        try:
            data = json.loads(stdout.decode())
            task_id = data.get("task_id")
            if task_id:
                return ToolResult.ok({
                    "success": True,
                    "task_id": task_id,
                    "prompt": prompt,
                    "message": f"Video-Generierung gestartet. Task-ID: {task_id}",
                })
            elif data.get("base_resp", {}).get("status_code") == 0:
                return ToolResult.ok({
                    "success": True,
                    "prompt": prompt,
                    "output_file": filename,
                })
            else:
                return ToolResult.fail(f"MiniMax Error: {stdout.decode()}")
        except json.JSONDecodeError:
            return ToolResult.fail(f"Keine gültige JSON-Antwort: {stdout.decode()[:200]}")
            
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout nach 300s — Video-Generierung zu langsam")
    except Exception as e:
        return ToolResult.fail(f"Video-Generierung fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="video",
    description="Generiert Videos mit MiniMax AI.",
    schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Szene-Beschreibung"},
            "duration": {"type": "integer", "description": "Dauer in Sekunden"},
        },
        "required": ["prompt"],
    },
    execute=_execute,
)

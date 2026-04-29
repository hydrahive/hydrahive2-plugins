"""video — Generiert Videos mit MiniMax AI."""
import asyncio
import subprocess
import json
from pathlib import Path
from datetime import datetime

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    prompt = args.get("prompt", "")
    duration = args.get("duration", 5)  # seconds
    output = args.get("output", None)
    
    if not prompt:
        return ToolResult.fail("prompt ist erforderlich")
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output or f"mmx_video_{timestamp}.mp4"
    
    # Build command
    cmd = ["mmx", "video", "generate", "--prompt", prompt]
    if duration:
        cmd.extend(["--duration", str(duration)])
    cmd.extend(["--output", filename])
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        result = stdout.decode() + stderr.decode()
        
        # Check for task ID (video generation is async)
        try:
            data = json.loads(result)
            task_id = data.get("task_id")
            if task_id:
                return ToolResult.ok({
                    "success": True,
                    "task_id": task_id,
                    "prompt": prompt,
                    "message": "Video-Generierung gestartet. Task-ID: " + task_id,
                    "check_status": f"Nutze mmx video task get --task-id {task_id}",
                })
            elif data.get("base_resp", {}).get("status_code") == 0:
                return ToolResult.ok({
                    "success": True,
                    "prompt": prompt,
                    "output": filename,
                    "message": "Video erfolgreich generiert!",
                })
        except json.JSONDecodeError:
            pass
        
        return ToolResult.ok({
            "success": True,
            "prompt": prompt,
            "raw_output": result[:500],
        })
            
    except Exception as e:
        return ToolResult.fail(f"Video-Generierung fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="video",
    description="Generiert Videos mit MiniMax AI. Beschreibe die Szene.",
    schema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Beschreibung der Szene im Video",
            },
            "duration": {
                "type": "integer",
                "description": "Dauer in Sekunden (default: 5)",
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

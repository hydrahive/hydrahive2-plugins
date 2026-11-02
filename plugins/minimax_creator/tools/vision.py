"""vision — Bildanalyse mit MiniMax AI."""
import asyncio
import json

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from ._mmx import minimax_api_key, mmx_base_cmd, mmx_binary, missing_key_message


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    image = args.get("image", "")
    prompt = args.get("prompt", None)

    if not image:
        return ToolResult.fail("image ist erforderlich (Pfad oder URL)")

    if not mmx_binary():
        return ToolResult.fail("mmx-CLI fehlt (npm install -g mmx-cli)")

    api_key = minimax_api_key()
    if not api_key:
        return ToolResult.fail(missing_key_message())

    cmd = [*mmx_base_cmd(api_key), "vision", "describe", "--image", image]
    if prompt:
        cmd.extend(["--prompt", prompt])
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        
        # Nur stdout parsen
        try:
            data = json.loads(stdout.decode())
            description = data.get("content", "")
            if description:
                return ToolResult.ok({
                    "success": True,
                    "image": image,
                    "description": description,
                })
            else:
                return ToolResult.fail(f"Keine Beschreibung in Antwort: {stdout.decode()[:200]}")
        except json.JSONDecodeError:
            return ToolResult.fail(f"Keine gültige JSON-Antwort: {stdout.decode()[:200]}")
            
    except asyncio.TimeoutError:
        return ToolResult.fail("Timeout nach 60s — Bild-Analyse zu langsam")
    except Exception as e:
        return ToolResult.fail(f"Bild-Analyse fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="vision",
    description="Analysiert ein Bild mit MiniMax Vision.",
    schema={
        "type": "object",
        "properties": {
            "image": {"type": "string", "description": "Bild-Pfad oder URL"},
            "prompt": {"type": "string", "description": "Optional: Frage zum Bild"},
        },
        "required": ["image"],
    },
    execute=_execute,
)

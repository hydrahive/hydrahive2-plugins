"""hello — gibt eine Nachricht zurück. Reines Demo-Tool ohne Seiteneffekte."""
from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    message = args.get("message") or "Hallo aus dem hello-world-Plugin!"
    return ToolResult.ok(f"hello-world echo: {message}")


TOOL = Tool(
    name="hello",
    description=(
        "Demo-Tool aus dem hello-world-Plugin. Gibt die übergebene Nachricht "
        "als Antwort zurück. Wenn keine Nachricht angegeben ist, kommt ein "
        "Default-Gruß."
    ),
    schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Optional — die Nachricht, die zurückgegeben werden soll.",
            }
        },
        "required": [],
    },
    execute=_execute,
)

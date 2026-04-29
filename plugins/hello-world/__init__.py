"""hello-world: Demo-Plugin für HydraHive2.

Registriert ein einzelnes Echo-Tool. Dient als Vorlage für eigene Plugins.
"""
from hello_world.tools.hello import TOOL as HELLO_TOOL


def on_load(ctx) -> None:
    """Wird beim Backend-Start aufgerufen, sobald das Plugin gefunden wurde."""
    ctx.register_tool(HELLO_TOOL)
    ctx.logger.info("hello-world bereit (1 Tool)")

"""HTTP Tester Plugin für HydraHive2.

Tools für API-Tests und JSON-Validierung.
"""
from http_tester.tools.request import TOOL as REQUEST_TOOL
from http_tester.tools.compare import TOOL as COMPARE_TOOL
from http_tester.tools.validate import TOOL as VALIDATE_TOOL


def on_load(ctx) -> None:
    ctx.register_tool(REQUEST_TOOL)
    ctx.register_tool(COMPARE_TOOL)
    ctx.register_tool(VALIDATE_TOOL)
    ctx.logger.info("http_tester Plugin geladen: request, compare, validate")

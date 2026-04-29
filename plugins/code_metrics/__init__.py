"""Code-Metrics Plugin für HydraHive2.

Bietet Tools für Code-Analyse und Projekt-Metriken.
"""
from code_metrics.tools.loc import TOOL as LOC_TOOL
from code_metrics.tools.languages import TOOL as LANGUAGES_TOOL
from code_metrics.tools.files import TOOL as FILES_TOOL
from code_metrics.tools.complexity import TOOL as COMPLEXITY_TOOL


def on_load(ctx) -> None:
    """Register all code-metrics tools."""
    ctx.register_tool(LOC_TOOL)
    ctx.register_tool(LANGUAGES_TOOL)
    ctx.register_tool(FILES_TOOL)
    ctx.register_tool(COMPLEXITY_TOOL)
    ctx.logger.info("code-metrics Plugin geladen: 4 Tools verfügbar")

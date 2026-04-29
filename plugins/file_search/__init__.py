"""File-Search Plugin für HydraHive2.

Erweiterte Such-Tools für Codebase-Navigation.
"""
from file_search.tools.grep import TOOL as GREP_TOOL
from file_search.tools.find import TOOL as FIND_TOOL
from file_search.tools.tree import TOOL as TREE_TOOL


def on_load(ctx) -> None:
    """Register all file-search tools."""
    ctx.register_tool(GREP_TOOL)
    ctx.register_tool(FIND_TOOL)
    ctx.register_tool(TREE_TOOL)
    ctx.logger.info("file-search Plugin geladen: 3 Tools verfügbar")

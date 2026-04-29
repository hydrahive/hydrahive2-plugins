"""Git-Stats Plugin für HydraHive2.

Bietet Tools für Git-Analytics direkt im Agent-Context.
"""
from hydrahive.tools.base import Tool, ToolContext, ToolResult

# Import all tools
from git_stats.tools.commits import TOOL as COMMITS_TOOL
from git_stats.tools.authors import TOOL as AUTHORS_TOOL
from git_stats.tools.files import TOOL as FILES_TOOL
from git_stats.tools.diff import TOOL as DIFF_TOOL


def on_load(ctx) -> None:
    """Register all git-stats tools."""
    ctx.register_tool(COMMITS_TOOL)
    ctx.register_tool(AUTHORS_TOOL)
    ctx.register_tool(FILES_TOOL)
    ctx.register_tool(DIFF_TOOL)
    ctx.logger.info("git-stats Plugin geladen: 4 Tools verfügbar")

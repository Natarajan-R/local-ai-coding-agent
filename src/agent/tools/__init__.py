"""Agent tools: parsing model output and executing tool calls."""
from .parser import ToolCall, ToolParser
from .patcher import apply_search_replace, make_diff
from .registry import Tool, ToolRegistry, ToolResult

__all__ = [
    "ToolCall",
    "ToolParser",
    "apply_search_replace",
    "make_diff",
    "Tool",
    "ToolRegistry",
    "ToolResult",
]

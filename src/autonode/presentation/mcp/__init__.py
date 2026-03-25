"""
MCP server (presentation): exposes Autonode capabilities to MCP clients over stdio.
"""

from autonode.presentation.mcp.server import run_mcp_server

__all__ = ["run_mcp_server"]

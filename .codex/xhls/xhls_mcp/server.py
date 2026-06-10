"""XHLS MCP Server — exposes ContextEngine over Model Context Protocol."""

import asyncio
import logging
import sys
import os

# Ensure .codex/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server import Server
from mcp.server.stdio import stdio_server

from xhls.xhls_mcp.tools import register_tools

logger = logging.getLogger(__name__)


def create_server() -> Server:
    """Create and configure the XHLS MCP server."""
    server = Server("xhls-mcp")
    register_tools(server)
    return server


async def run_stdio():
    """Run via stdio transport (for Codex CLI integration)."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        logger.info("XHLS MCP Bridge starting on stdio...")
        await server.run(
            read_stream, write_stream,
            server.create_initialization_options(),
        )


async def run_sse(host: str = "127.0.0.1", port: int = 8200):
    """Run via SSE/HTTP transport (for external clients)."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    import uvicorn

    server = create_server()
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream,
                server.create_initialization_options(),
            )

    async def handle_messages(request):
        await sse.handle_post_message(
            request.scope, request.receive, request._send
        )

    app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages/", endpoint=handle_messages, methods=["POST"]),
        ],
    )

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    http_server = uvicorn.Server(config)
    logger.info(f"XHLS MCP Bridge starting on SSE at {host}:{port}...")
    await http_server.serve()

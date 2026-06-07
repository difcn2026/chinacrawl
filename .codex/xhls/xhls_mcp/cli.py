"""XHLS MCP Bridge CLI.

Usage:
  python -m xhls.xhls_mcp.cli serve            # stdio mode (for Codex)
  python -m xhls.xhls_mcp.cli serve --sse      # SSE mode (HTTP)
  python -m xhls.xhls_mcp.cli serve --port 8200 # SSE with custom port
"""

import argparse
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)


def main():
    parser = argparse.ArgumentParser(description="XHLS MCP Bridge")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start MCP server")
    serve.add_argument("--sse", action="store_true", help="Use SSE transport (default: stdio)")
    serve.add_argument("--host", default="127.0.0.1", help="SSE host (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8200, help="SSE port (default: 8200)")

    args = parser.parse_args()

    if args.command == "serve":
        from xhls.xhls_mcp.server import run_stdio, run_sse
        if args.sse:
            asyncio.run(run_sse(host=args.host, port=args.port))
        else:
            asyncio.run(run_stdio())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

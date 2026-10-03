"""MCP server exposing Freshdesk read-only tools (SDK v2).

Run with:  python -m src.mcp_server
Transport: stdio (default for MCPServer.run()).
"""

from __future__ import annotations

import json
import logging
import sys

from mcp.server import MCPServer

from .freshdesk_client import (
    FreshdeskClient,
    FreshdeskError,
    FreshdeskAuthError,
    FreshdeskNotFoundError,
)

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = MCPServer("freshdesk-agent-connector")
client = FreshdeskClient()


@mcp.tool()
def list_tickets(page: int = 1, per_page: int = 30) -> str:
    """List Freshdesk tickets, paginated.

    Returns ticket summaries (id, subject, status, priority, requester_id, created_at).
    Use page/per_page to page through results; per_page is capped at 100.
    """
    try:
        data = client.list_tickets(page=page, per_page=per_page)
        return json.dumps(data, indent=2, default=str)
    except FreshdeskError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_ticket(ticket_id: int) -> str:
    """Fetch full details of a single Freshdesk ticket by ID."""
    try:
        data = client.get_ticket(ticket_id)
        return json.dumps(data, indent=2, default=str)
    except FreshdeskNotFoundError as e:
        return json.dumps({"error": f"Not found: {e}"})
    except FreshdeskAuthError as e:
        return json.dumps({"error": f"Authentication failed: {e}"})
    except FreshdeskError as e:
        return json.dumps({"error": f"Freshdesk error: {e}"})


@mcp.tool()
def search_tickets(query: str) -> str:
    """Search Freshdesk tickets using Freshdesk query syntax.

    Examples: 'status:2' (open), 'priority:3' (high), 'requester:12345'.
    Combine with AND/OR. Query is auto-wrapped in quotes.
    """
    try:
        data = client.search_tickets(query)
        return json.dumps(data, indent=2, default=str)
    except FreshdeskError as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
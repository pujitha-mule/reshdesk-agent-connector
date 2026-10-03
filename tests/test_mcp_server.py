"""Integration tests for the MCP server using the v2 Client.

Verifies the server advertises the expected tools and that tool invocation
routes through to the Freshdesk client.
"""

from __future__ import annotations

import os
import json
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("FRESHDESK_DOMAIN", "test.freshdesk.com")
os.environ.setdefault("FRESHDESK_API_KEY", "testkey")

from mcp import Client  # noqa: E402

from src.mcp_server import mcp  # noqa: E402


@pytest.mark.asyncio
async def test_server_advertises_expected_tools():
    async with Client(mcp) as c:
        tools = await c.list_tools()
        names = {t.name for t in tools.tools}
        assert names == {"list_tickets", "get_ticket", "search_tickets"}


@pytest.mark.asyncio
async def test_list_tickets_routes_through_client():
    fake = [{"id": 1, "subject": "hi"}]
    with patch("src.mcp_server.client.list_tickets", return_value=fake):
        async with Client(mcp) as c:
            result = await c.call_tool("list_tickets", {"page": 1, "per_page": 5})
            text = result.content[0].text
            assert json.loads(text) == fake
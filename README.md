# Freshdesk Agent Connector

A read-only MCP connector that lets an Agent Studio agent retrieve merchant
support data from Freshdesk.

Built as the Option 3 submission for the Razorpay Forward-Deployed Engineer,
Agent Studio assignment.

## Setup

1. **Get Freshdesk credentials.** Find your API key at
   *Profile Settings → Your API Key*.
2. **Install:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Configure:**
   ```bash
   copy .env.example .env
   # edit .env with real FRESHDESK_DOMAIN and FRESHDESK_API_KEY
   ```

## Running

```bash
python -m scripts.demo       # real-account demo
python -m src.mcp_server     # MCP server (stdio)
pytest -v                    # all tests (mocked HTTP)
```

## MCP tool specification

| Tool | Purpose | Input | Output |
| --- | --- | --- | --- |
| `list_tickets` | List tickets, paginated | `page`, `per_page` | ticket summaries |
| `get_ticket` | Fetch one ticket by ID | `ticket_id` | full ticket |
| `search_tickets` | Search via Freshdesk query DSL | `query` | matching tickets |

### Tool details

**`list_tickets`**
- `page` (int, ≥1, default 1)
- `per_page` (int, 1–100, default 30; clamped server-side)

**`get_ticket`**
- `ticket_id` (int, required)

**`search_tickets`**
- `query` (string, required). Freshdesk syntax, e.g. `status:2`,
  `priority:3`, `requester:12345`, combined with `AND`/`OR`.

## Authentication

Freshdesk **API-key authentication** via HTTP Basic:
- Username = API key
- Password = literal `"X"`

The assignment permits API-key auth. Credentials load from environment
variables and are never logged.

## Rate limiting & resilience

Handled centrally in `FreshdeskClient._request()`:

| Condition | Behaviour |
| --- | --- |
| `429` | Read `Retry-After` (capped 60s), sleep, retry up to **5 attempts**. |
| `5xx` | Exponential backoff, up to 3 attempts (1s → 2s → 4s). |
| `401 / 403` | Raise `FreshdeskAuthError`; no key leakage. |
| `404` | Raise `FreshdeskNotFoundError`; surfaced as tool-level JSON error. |
| `4xx` (other) | Raise `FreshdeskError` with truncated body. |
| Network / timeout | Raise `FreshdeskError`; no full URL in message. |

## What the agent **can** do

- Retrieve Freshdesk tickets (paginated list)
- Search tickets with Freshdesk query syntax
- Retrieve full details of an individual ticket
- Handle temporary API failures transparently (5xx retries)
- Respect Freshdesk rate limits (429 + `Retry-After`, bounded)
- Surface auth and not-found errors as structured JSON

## What the agent **cannot** do

- **Create** tickets
- **Update** or modify tickets
- **Delete** tickets
- **Send replies** or add notes
- Access resources outside the authenticated account
- Bypass Freshdesk permissions or plan limits
- Retrieve non-ticket resources (contacts, companies, agents, etc.)
- Perform any write operation

This connector is intentionally **read-only**.

## Known limitations

- **Pagination:** `list_tickets` exposes page-based pagination so the agent
  can request subsequent pages without loading an unbounded result set.
- **Search syntax:** Freshdesk’s search DSL passes through verbatim; bad
  queries surface as Freshdesk 4xx errors rather than local validation.
- **No caching.** Every tool call hits the Freshdesk API.
- **stdio transport only.**
- **Single-tenant.** One credential set per process.

## Project layout

```
freshdesk-agent-connector/
├── src/
│   ├── freshdesk_client.py
│   └── mcp_server.py
├── tests/
│   ├── test_client.py
│   └── test_mcp_server.py
├── scripts/
│   └── demo.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
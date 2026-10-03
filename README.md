# Freshdesk Agent Connector

A read-only MCP connector that enables an Agent Studio agent to retrieve merchant support data from Freshdesk.

Built as the **Option 3 submission** for the Razorpay **Forward-Deployed Engineer, Agent Studio** assignment.

---

## What This Connector Does

This connector provides an Agent Studio agent with three read-only Freshdesk tools:

- **List tickets** with pagination
- **Get a ticket** by ID
- **Search tickets** using Freshdesk query syntax

The connector uses Freshdesk API-key authentication and includes bounded retry handling for rate limits and temporary server failures.

---

## Key Capabilities

| Capability | Implementation |
|---|---|
| Freshdesk authentication | API key + HTTP Basic Auth |
| List tickets | `list_tickets` |
| Get ticket | `get_ticket` |
| Search tickets | `search_tickets` |
| Rate-limit handling | HTTP 429 + `Retry-After` |
| Temporary failure handling | HTTP 5xx exponential backoff |
| Error handling | Auth, not-found, client, timeout/network errors |
| Agent interface | MCP tools |
| Data access | Read-only |
| Tests | 15 automated tests |
| Transport | MCP stdio |

---

## Project Structure

```text
freshdesk-agent-connector/
├── src/
│   ├── __init__.py
│   ├── freshdesk_client.py
│   └── mcp_server.py
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   └── test_mcp_server.py
├── scripts/
│   ├── __init__.py
│   └── demo.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- A Freshdesk account
- Freshdesk API key

The connector reads credentials from environment variables.

### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure credentials

Copy the example environment file:

```powershell
copy .env.example .env
```

Then edit `.env`:

```env
FRESHDESK_DOMAIN=yourcompany.freshdesk.com
FRESHDESK_API_KEY=your_api_key_here
```

The API key can be obtained from:

**Freshdesk → Profile Settings → Your API Key**

### Security

- `.env` is excluded through `.gitignore`.
- API keys are loaded from environment variables.
- Credentials are never logged.
- Do not commit `.env` or real credentials.

---

## MCP Tools

The connector exposes three MCP tools.

### 1. `list_tickets`

Lists Freshdesk tickets using page-based pagination.

**Inputs:**

| Parameter | Type | Default | Description |
|---|---|---:|---|
| `page` | integer | `1` | Page number; minimum 1 |
| `per_page` | integer | `30` | Number of tickets; limited to 1–100 |

**Example:**

```text
list_tickets(page=1, per_page=30)
```

---

### 2. `get_ticket`

Retrieves a specific Freshdesk ticket.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `ticket_id` | integer | Freshdesk ticket ID |

**Example:**

```text
get_ticket(ticket_id=123)
```

---

### 3. `search_tickets`

Searches Freshdesk tickets using Freshdesk query syntax.

**Input:**

| Parameter | Type | Description |
|---|---|---|
| `query` | string | Freshdesk search query |

**Examples:**

```text
status:2
```

```text
priority:3
```

```text
requester:12345
```

Freshdesk query syntax can also be combined using supported query operators.

---

## Authentication

Freshdesk API-key authentication is implemented using HTTP Basic Authentication:

```text
Username = Freshdesk API key
Password = X
```

Credentials are supplied through:

```env
FRESHDESK_DOMAIN=...
FRESHDESK_API_KEY=...
```

No credentials are hard-coded into the application.

---

## Reliability and Error Handling

All Freshdesk HTTP requests are handled centrally by `FreshdeskClient`.

### Rate Limits

When Freshdesk returns `429 Too Many Requests`:

1. Read the `Retry-After` header.
2. Wait for the requested duration.
3. Retry the request.
4. Cap the wait at 60 seconds.
5. Stop after a bounded number of attempts.

This prevents unbounded retry loops.

### Server Errors

For HTTP 5xx responses, the connector uses exponential backoff:

```text
1s → 2s → 4s
```

with a maximum of 3 attempts.

### Other Errors

| HTTP status / condition | Behaviour |
|---|---|
| `401` | Authentication error |
| `403` | Authentication/permission error |
| `404` | Resource not found |
| Other `4xx` | Freshdesk error with truncated response |
| Timeout | Connector error |
| Network failure | Connector error |

Sensitive credentials and full request URLs are not exposed in error messages.

---

## What the Agent Can Do

The Agent Studio agent can:

- Retrieve Freshdesk tickets
- Retrieve tickets page by page
- Retrieve an individual ticket by ID
- Search tickets using Freshdesk query syntax
- Handle temporary Freshdesk server failures
- Respect Freshdesk rate limits
- Surface authentication and not-found errors

---

## What the Agent Cannot Do

This connector is intentionally **read-only**.

The agent cannot:

- Create tickets
- Update tickets
- Delete tickets
- Send ticket replies
- Add ticket notes
- Modify Freshdesk data
- Access resources outside the authenticated Freshdesk account
- Bypass Freshdesk permissions or plan restrictions
- Retrieve non-ticket resources such as contacts, companies, or agents
- Perform any other write operation

---

## Testing

The project includes unit tests for the Freshdesk client and MCP integration tests.

Run:

```powershell
pytest -v
```

### Test Result

```text
15 passed
```

The tests cover:

- Ticket listing
- Pagination bounds
- Ticket retrieval
- Ticket search
- Empty search validation
- 401/403 authentication errors
- 404 handling
- 429 retry behaviour
- Bounded 429 retries
- 5xx retry behaviour
- Bounded 5xx retries
- Timeout handling
- MCP tool discovery
- MCP tool-to-client routing

HTTP interactions are mocked in the automated tests.

---

## Real-Account Demo

A demo script is included to verify the connector against a configured Freshdesk account.

Run:

```powershell
python -m scripts.demo
```

The demo exercises:

1. `list_tickets`
2. `get_ticket`
3. `search_tickets`

No real-account output or customer data is included in this repository.

---

## Running the MCP Server

Start the MCP server over stdio:

```powershell
python -m src.mcp_server
```

The server waits for an MCP client to connect.

The MCP integration tests verify that the server advertises:

```text
list_tickets
get_ticket
search_tickets
```

---

## Limitations and Assumptions

- **Read-only:** No Freshdesk write operations are implemented.
- **Pagination:** Ticket listing uses page-based pagination.
- **Search:** Freshdesk query syntax is passed through to the API; invalid queries are returned as Freshdesk errors.
- **No caching:** Each tool call makes a Freshdesk API request.
- **Single tenant:** One Freshdesk credential set is used per running process.
- **stdio only:** The connector currently exposes MCP through stdio transport.
- **Ticket scope:** The connector currently focuses on Freshdesk ticket retrieval and search.

---

## Assignment Mapping

This implementation addresses the Razorpay Option 3 requirements:

| Razorpay Requirement | Implementation |
|---|---|
| Choose a merchant tool | Freshdesk |
| Read merchant data | Freshdesk tickets |
| Authentication | API key |
| List primitive | `list_tickets` |
| Get primitive | `get_ticket` |
| Search primitive | `search_tickets` |
| Rate-limit handling | 429 + `Retry-After` |
| MCP specification | MCP server + tool definitions |
| Agent capabilities documented | Yes |
| Agent limitations documented | Yes |
| Setup/run instructions | Yes |
| Assumptions/limitations | Yes |
| Automated testing | 15 tests passing |
| Real API verification | Demo script |
| Real credentials excluded | `.env` ignored |
| Real customer/demo data excluded | Yes |

---

## Technologies

- Python
- Freshdesk REST API
- MCP
- Requests
- pytest
- pytest-asyncio
- python-dotenv

---

## Security Note

Never commit:

```text
.env
```

or any real API keys, passwords, access tokens, or customer data.

Use `.env.example` for placeholder configuration only.

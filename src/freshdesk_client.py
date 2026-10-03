"""Freshdesk API client.

Single request path handles: API-key auth, timeouts, bounded 429 rate limits,
5xx retries, and 4xx error mapping. All MCP tools go through this client.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
MAX_RETRIES_5XX = 3
MAX_RETRIES_429 = 5
BACKOFF_BASE = 1.0
MAX_RETRY_AFTER = 60


class FreshdeskError(Exception):
    """Base error for Freshdesk client."""


class FreshdeskAuthError(FreshdeskError):
    """401/403 from Freshdesk."""


class FreshdeskNotFoundError(FreshdeskError):
    """404 from Freshdesk."""


class FreshdeskRateLimitError(FreshdeskError):
    """429 that persisted past MAX_RETRIES_429."""


class FreshdeskClient:
    def __init__(
        self,
        domain: str | None = None,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        domain = domain or os.getenv("FRESHDESK_DOMAIN")
        api_key = api_key or os.getenv("FRESHDESK_API_KEY")

        if not domain or not api_key:
            raise FreshdeskError(
                "FRESHDESK_DOMAIN and FRESHDESK_API_KEY must be set "
                "(env vars or constructor args)."
            )

        domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
        self.base_url = f"https://{domain}/api/v2"
        self.auth = (api_key, "X")
        self.timeout = timeout
        self.session = requests.Session()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        attempt_5xx = 0
        attempt_429 = 0

        while True:
            try:
                resp = self.session.request(
                    method,
                    url,
                    auth=self.auth,
                    params=params,
                    timeout=self.timeout,
                    headers={"Accept": "application/json"},
                )
            except requests.Timeout as e:
                raise FreshdeskError(
                    f"Request timed out after {self.timeout}s."
                ) from e
            except requests.RequestException as e:
                raise FreshdeskError(f"Network error: {e}") from e

            # --- rate limit (bounded) ---
            if resp.status_code == 429:
                attempt_429 += 1
                if attempt_429 > MAX_RETRIES_429:
                    raise FreshdeskRateLimitError(
                        f"Freshdesk 429 after {MAX_RETRIES_429} retries."
                    )
                wait = self._retry_after_seconds(resp)
                logger.warning(
                    "429 from Freshdesk; retry %d/%d in %.1fs",
                    attempt_429, MAX_RETRIES_429, wait,
                )
                time.sleep(wait)
                continue

            # --- transient server errors ---
            if 500 <= resp.status_code < 600:
                attempt_5xx += 1
                if attempt_5xx > MAX_RETRIES_5XX:
                    raise FreshdeskError(
                        f"Freshdesk {resp.status_code} after {MAX_RETRIES_5XX} retries."
                    )
                wait = BACKOFF_BASE * (2 ** (attempt_5xx - 1))
                logger.warning(
                    "%s from Freshdesk; retry %d/%d in %.1fs",
                    resp.status_code, attempt_5xx, MAX_RETRIES_5XX, wait,
                )
                time.sleep(wait)
                continue

            # --- auth ---
            if resp.status_code in (401, 403):
                raise FreshdeskAuthError(
                    f"Freshdesk auth failed ({resp.status_code}). "
                    "Check FRESHDESK_API_KEY and account permissions."
                )

            # --- not found ---
            if resp.status_code == 404:
                raise FreshdeskNotFoundError(f"Not found: {path}")

            # --- other 4xx ---
            if 400 <= resp.status_code < 500:
                raise FreshdeskError(
                    f"Freshdesk {resp.status_code}: {resp.text[:300]}"
                )

            # --- success ---
            if resp.status_code == 204 or not resp.content:
                return None
            return resp.json()

    @staticmethod
    def _retry_after_seconds(resp: requests.Response) -> float:
        raw = resp.headers.get("Retry-After")
        if raw is None:
            return 1.0
        try:
            return min(float(raw), MAX_RETRY_AFTER)
        except ValueError:
            return 1.0

    def list_tickets(self, page: int = 1, per_page: int = 30) -> list[dict]:
        """List tickets, paginated. per_page capped at 100 by Freshdesk."""
        page = max(1, int(page))
        per_page = max(1, min(int(per_page), 100))
        data = self._request(
            "GET", "/tickets", params={"page": page, "per_page": per_page}
        )
        return data or []

    def get_ticket(self, ticket_id: int) -> dict:
        """Fetch a single ticket by ID."""
        return self._request("GET", f"/tickets/{int(ticket_id)}")

    def search_tickets(self, query: str) -> list[dict]:
        """Search tickets. `query` uses Freshdesk search syntax, e.g. 'status:2'."""
        if not query or not query.strip():
            raise FreshdeskError("search_tickets requires a non-empty query.")
        data = self._request(
            "GET", "/search/tickets", params={"query": f'"{query}"'}
        )
        if isinstance(data, dict):
            return data.get("results", []) or []
        return data or []
"""Manual demo: exercise the client against a real Freshdesk account.

Usage:  python -m scripts.demo
Requires FRESHDESK_DOMAIN and FRESHDESK_API_KEY in .env.
"""

from __future__ import annotations

import json

from src.freshdesk_client import FreshdeskClient, FreshdeskError


def main() -> None:
    client = FreshdeskClient()

    print("== list_tickets (first 3) ==")
    try:
        tickets = client.list_tickets(page=1, per_page=3)
        for t in tickets:
            print(json.dumps(
                {k: t.get(k) for k in ("id", "subject", "status", "priority")},
                indent=2,
            ))
    except FreshdeskError as e:
        print(f"list_tickets failed: {e}")
        return

    if tickets:
        tid = tickets[0]["id"]
        print(f"\n== get_ticket({tid}) ==")
        detail = client.get_ticket(tid)
        print(json.dumps(
            {k: detail.get(k) for k in ("id", "subject", "status", "description_text")},
            indent=2,
        ))

    print("\n== search_tickets('status:2') ==")
    try:
        results = client.search_tickets("status:2")
        print(f"{len(results)} matching tickets")
    except FreshdeskError as e:
        print(f"search failed: {e}")


if __name__ == "__main__":
    main()
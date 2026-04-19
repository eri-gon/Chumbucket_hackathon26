#!/usr/bin/env python3
"""
POST /query against the deployed SAM API (Lambda → Athena) and print JSON.

Usage (repo root):

  set API_BASE_URL=https://xxxx.execute-api.us-west-1.amazonaws.com/Prod
  python scripts/test_query_api.py

Or rely on frontend/.env VITE_API_URL (same value as API base, no /query suffix).

  python scripts/test_query_api.py --metric temperature --depth 10
  python scripts/test_query_api.py --metric salinity --depth 50 --start-date 01/01/1949 --end-date 12/31/1949
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _load_frontend_dotenv() -> None:
    root = Path(__file__).resolve().parent.parent
    env_path = root / "frontend" / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val:
            os.environ.setdefault(key, val)


def _resolve_base_url() -> str:
    _load_frontend_dotenv()
    base = (
        os.environ.get("API_BASE_URL")
        or os.environ.get("VITE_API_URL")
        or ""
    ).strip().rstrip("/")
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="POST /query and print Athena-backed JSON.")
    parser.add_argument(
        "--url",
        default="",
        help="API base URL (no /query). Overrides API_BASE_URL / VITE_API_URL.",
    )
    parser.add_argument("--metric", default="temperature")
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--start-date", default="", dest="start_date")
    parser.add_argument("--end-date", default="", dest="end_date")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=20,
        help="Max rows from data[] to print in full (rest summarized).",
    )
    args = parser.parse_args()

    base = args.url.strip().rstrip("/") or _resolve_base_url()
    if not base:
        print(
            "Missing API URL. Set API_BASE_URL or VITE_API_URL, or pass --url.\n"
            "Example: set API_BASE_URL=https://abc123.execute-api.us-west-1.amazonaws.com/Prod",
            file=sys.stderr,
        )
        return 1

    payload: dict = {"metric": args.metric, "depth": args.depth}
    if args.start_date:
        payload["startDate"] = args.start_date
    if args.end_date:
        payload["endDate"] = args.end_date

    url = f"{base}/query"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    print(f"POST {url}")
    print(f"Body: {json.dumps(payload)}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        status = e.code
        print(f"\nHTTP {status}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(raw)
        return 1

    print(f"\nHTTP {status}")
    rows = data.get("data") if isinstance(data, dict) else None
    if isinstance(rows, list) and len(rows) > args.max_rows:
        summary = {
            **{k: v for k, v in data.items() if k != "data"},
            "data": rows[: args.max_rows],
            "_truncated": f"{len(rows) - args.max_rows} more row(s); increase --max-rows to print all",
        }
        print(json.dumps(summary, indent=2))
    else:
        print(json.dumps(data, indent=2))

    if isinstance(data, dict) and data.get("success") is False:
        return 1
    if status >= 400:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

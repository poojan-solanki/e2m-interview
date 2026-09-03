"""Thin Supabase REST (PostgREST) + Storage client using httpx directly.

No supabase-py SDK — the project already depends on httpx, and Supabase's REST/Storage
APIs are plain HTTP, so a small direct client avoids an extra heavy dependency.

All calls use the service-role key, so they bypass Row Level Security entirely — this
module is backend-only (never imported by anything exposed to the browser). Every
generated artifact (source photo, per-zone masks, canny control image, rendered
image, comparison strip) lives in the "studio-assets" Storage bucket; the backend
process itself stores nothing persistently on local disk.
"""

import os
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "studio-assets"


def is_configured() -> bool:
    return bool(SUPABASE_URL and SERVICE_ROLE_KEY)


def _require_configured() -> None:
    if not is_configured():
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "in backend/.env (service_role key is in the Supabase dashboard under "
            "Project Settings -> API -- never the anon key)."
        )


def _headers(content_type: Optional[str] = None) -> dict:
    h = {"apikey": SERVICE_ROLE_KEY, "Authorization": f"Bearer {SERVICE_ROLE_KEY}"}
    if content_type:
        h["Content-Type"] = content_type
    return h


# --- Storage -----------------------------------------------------------------


def upload_bytes(storage_path: str, content: bytes, content_type: str) -> str:
    """Uploads bytes to the studio-assets bucket, returns the public URL."""
    _require_configured()
    resp = httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}",
        headers={**_headers(content_type), "x-upsert": "true"},
        content=content,
        timeout=60,
    )
    resp.raise_for_status()
    return public_url(storage_path)


def upload_file(storage_path: str, local_path: Path, content_type: str) -> str:
    return upload_bytes(storage_path, local_path.read_bytes(), content_type)


def public_url(storage_path: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{storage_path}"


def download_bytes(storage_path: str) -> bytes:
    _require_configured()
    resp = httpx.get(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}",
        headers=_headers(),
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


# --- Postgres (PostgREST) -----------------------------------------------------


def insert_row(table: str, row: dict) -> dict:
    _require_configured()
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_headers("application/json"), "Prefer": "return=representation"},
        json=row,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()[0]


def insert_rows(table: str, rows: list) -> list:
    _require_configured()
    if not rows:
        return []
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_headers("application/json"), "Prefer": "return=representation"},
        json=rows,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def upsert_row(table: str, row: dict, on_conflict: str) -> dict:
    _require_configured()
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}",
        headers={
            **_headers("application/json"),
            "Prefer": "return=representation,resolution=merge-duplicates",
        },
        json=row,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()[0]


def update_row(table: str, id_column: str, id_value: str, patch: dict) -> Optional[dict]:
    _require_configured()
    resp = httpx.patch(
        f"{SUPABASE_URL}/rest/v1/{table}?{id_column}=eq.{id_value}",
        headers={**_headers("application/json"), "Prefer": "return=representation"},
        json=patch,
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def get_row(table: str, id_column: str, id_value: str) -> Optional[dict]:
    _require_configured()
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{table}?{id_column}=eq.{id_value}&select=*",
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def query(table: str, filters: dict, select: str = "*") -> list:
    _require_configured()
    params = "&".join(f"{k}=eq.{v}" for k, v in filters.items())
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
    if params:
        url += f"&{params}"
    resp = httpx.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()

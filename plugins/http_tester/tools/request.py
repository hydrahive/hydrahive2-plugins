"""request — HTTP Request Tool für HydraHive2.

Nutzt den zentralen SSRF-Schutz des Core (hydrahive.net.ssrf.safe_async_client,
wie fetch_url): nur http/https, keine internen/privaten Ziele, geprüfte IP
wird angepinnt (kein DNS-Rebinding), Weiterleitungen werden nicht verfolgt.
Vorher lief das Werkzeug über ein externes Kommandozeilenprogramm ohne jede
Prüfung (Task 3bd963b2 d, 01.10.2026) — localhost, LAN, Cloud-Metadaten und
file:// waren erreichbar.
"""
import json
import time

import httpx
from hydrahive.net.ssrf import SsrfBlocked, safe_async_client
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_MAX_BYTES = 200_000
_MAX_TIMEOUT = 60
_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}


def _clean_headers(raw) -> dict[str, str]:
    out = {"Content-Type": "application/json"}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if str(k).lower() == "host":  # Host-Header gehört dem Pinning
            continue
        out[str(k)] = str(v)
    return out


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    url = (args.get("url") or "").strip()
    method = str(args.get("method") or "GET").upper()
    body = args.get("body")
    try:
        timeout = max(1, min(int(args.get("timeout", 10)), _MAX_TIMEOUT))
    except (TypeError, ValueError):
        timeout = 10

    if not url:
        return ToolResult.fail("URL ist erforderlich")
    if method not in _METHODS:
        return ToolResult.fail(f"Methode {method} nicht erlaubt")

    start_time = time.time()
    try:
        async with safe_async_client(url, timeout=timeout) as client:
            r = await client.request(
                method, url, headers=_clean_headers(args.get("headers")),
                content=json.dumps(body).encode("utf-8") if body else None,
            )
    except SsrfBlocked as e:
        if str(e) == "scheme_not_allowed":
            return ToolResult.fail("Protokoll nicht erlaubt (nur http/https)")
        return ToolResult.fail(f"Zugriff auf interne/private Adressen gesperrt ({e})")
    except httpx.TimeoutException:
        return ToolResult.fail(f"Timeout nach {timeout}s")
    except httpx.HTTPError as e:
        return ToolResult.fail(f"Request fehlgeschlagen: {e}")

    elapsed = time.time() - start_time
    raw = r.content[:_MAX_BYTES].decode("utf-8", errors="replace")
    try:
        json_body = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        json_body = None
    return ToolResult.ok({
        "url": url,
        "method": method,
        "status_code": r.status_code,
        "elapsed_ms": round(elapsed * 1000, 2),
        "time_total_s": round(elapsed, 3),
        "body": json_body if json_body is not None else raw,
        "body_raw": raw[:1000],
        "success": 200 <= r.status_code < 300,
        "truncated": len(r.content) > _MAX_BYTES,
        "redirect_to": r.headers.get("location") if r.is_redirect else None,
    })


TOOL = Tool(
    name="request",
    description=(
        "Führt HTTP Request aus (GET/POST/PUT/DELETE/PATCH) gegen öffentliche "
        "http(s)-Adressen. Gibt Status, Response-Body und Zeit zurück. Interne "
        "Adressen (localhost, LAN) sind gesperrt, Weiterleitungen werden nicht verfolgt."
    ),
    schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL für den Request (http/https, öffentlich)",
            },
            "method": {
                "type": "string",
                "enum": sorted(_METHODS),
                "description": "HTTP Methode (default: GET)",
            },
            "headers": {
                "type": "object",
                "description": "Optionale Headers als JSON",
            },
            "body": {
                "type": "object",
                "description": "Request Body für POST/PUT (wird als JSON gesendet)",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in Sekunden (default: 10, max 60)",
            },
        },
        "required": ["url"],
    },
    execute=_execute,
)

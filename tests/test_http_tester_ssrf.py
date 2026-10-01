"""http-tester request: keine Anfragen ins interne Netz (Task 3bd963b2 d, 01.10.2026).

Vorher rief das Werkzeug curl ohne jede Prüfung auf: localhost, 192.168.x,
169.254.169.254 (Cloud-Metadaten), file:// und Weiterleitungen auf interne
Ziele waren möglich. Jetzt nutzt es den zentralen SSRF-Schutz des Core
(hydrahive.net.ssrf.safe_async_client wie fetch_url): interne Ziele gesperrt,
geprüfte IP angepinnt (kein DNS-Rebinding), keine Weiterleitungen.
"""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib

import httpx
import pytest
from hydrahive.tools.base import ToolContext

TOOL_FILE = pathlib.Path(__file__).resolve().parents[1] / "plugins" / "http_tester" / "tools" / "request.py"


def _tool():
    spec = importlib.util.spec_from_file_location("http_tester_request", TOOL_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(mod, args, tmp_path):
    ctx = ToolContext(session_id="s", agent_id="a", user_id="u", workspace=tmp_path)
    return asyncio.run(mod.TOOL.execute(args, ctx))


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8001/api/health",
    "http://localhost/",
    "http://192.168.178.1/",
    "http://10.0.0.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://0.0.0.0/",
    "file:///etc/passwd",
    "gopher://example.com/",
])
def test_interne_ziele_und_fremde_schemata_gesperrt(url, tmp_path):
    res = _run(_tool(), {"url": url}, tmp_path)
    assert not res.success, f"{url} hätte gesperrt sein müssen: {res.output}"
    assert "gesperrt" in (res.error or "") or "nicht erlaubt" in (res.error or "")


def test_kein_curl_mehr(tmp_path):
    """curl umgeht Pinning und folgt -L/Protokollen — das Werkzeug darf es nicht nutzen."""
    assert "curl" not in TOOL_FILE.read_text().split('"""', 2)[-1]


def test_oeffentliches_ziel_geht_und_wird_gepinnt(tmp_path, monkeypatch):
    mod = _tool()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.url.host
        seen["header"] = request.headers.get("host")
        return httpx.Response(200, json={"ok": True})

    real = mod.safe_async_client

    def fake_client(url, *, timeout):
        client = real(url, timeout=timeout)  # prüft + pinnt wie im Echtbetrieb
        pinned = client._transport
        transport = httpx.MockTransport(lambda r: handler(_pin(pinned, r)))
        return httpx.AsyncClient(timeout=timeout, follow_redirects=False, transport=transport)

    def _pin(pinned, request):
        from hydrahive.net.ssrf import pin_request
        return pin_request(request, pinned._pin)

    monkeypatch.setattr(mod, "safe_async_client", fake_client)
    monkeypatch.setattr("hydrahive.net.ssrf.socket.getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("93.184.215.14", 0))])
    res = _run(mod, {"url": "https://example.com/x", "method": "POST", "body": {"a": 1}}, tmp_path)
    assert res.success, res.error
    assert res.output["status_code"] == 200 and res.output["body"] == {"ok": True}
    assert seen["host"] == "93.184.215.14" and seen["header"] == "example.com"


def test_weiterleitung_wird_nicht_verfolgt(tmp_path, monkeypatch):
    mod = _tool()

    def fake_client(url, *, timeout):
        transport = httpx.MockTransport(
            lambda r: httpx.Response(302, headers={"location": "http://127.0.0.1:8001/"}))
        return httpx.AsyncClient(timeout=timeout, follow_redirects=False, transport=transport)

    monkeypatch.setattr(mod, "safe_async_client", fake_client)
    res = _run(mod, {"url": "https://example.com/"}, tmp_path)
    assert res.success and res.output["status_code"] == 302

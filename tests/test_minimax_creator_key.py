"""MiniMax-Creator: API-Key kommt aus der Kern-Konfiguration, nicht aus ~/.mmx.

Befund 02.11.2026: Die mmx-CLI liest ihren Key aus ~/.mmx/config.json. Dort stand
ein alter Key, den die API mit "invalid api key" ablehnte — jedes Creator-Werkzeug
scheiterte. Der Kern hat einen gültigen Key in der LLM-Konfiguration (Provider
"minimax"). Die Werkzeuge holen ihn jetzt von dort und reichen ihn per --api-key
an die CLI weiter.

Diese Tests sichern:
1. Der Key wird aus der Kern-Config gelesen (nicht aus ~/.mmx).
2. Der Key landet im mmx-Aufruf als --api-key.
3. Fehlt der Key, gibt es eine klare Fehlermeldung statt eines API-Fehlers.
4. Die CLI-Aufrufe der fünf Werkzeuge bleiben vollständig (kein Kommando verliert
   seine Parameter) — inklusive der Erkenntnis, dass mmx KEIN "music"-Kommando
   hat (siehe Test music).
"""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib

import pytest

from hydrahive.tools.base import ToolContext

ROOT = pathlib.Path(__file__).resolve().parents[1] / "plugins" / "minimax_creator"


def _mod(rel: str):
    """Tool-Modul laden. Die Werkzeuge importieren relativ (from ._mmx import …),
    deshalb wird das Paket unter einem importierbaren Namen aufgelöst."""
    import importlib
    import sys

    pkg_root = str(ROOT.parent)
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)
    return importlib.import_module(f"minimax_creator.tools.{rel}")


@pytest.fixture
def ws(tmp_path):
    return tmp_path / "ws"


@pytest.fixture
def ctx(ws):
    ws.mkdir(parents=True, exist_ok=True)
    return ToolContext(workspace=ws, agent_id="t", session_id="t", user_id="till")


# --- 1) Key aus der Kern-Config ------------------------------------------------

def test_key_comes_from_core_config(monkeypatch):
    """Der Key stammt aus llm._config (Provider 'minimax'), nicht aus ~/.mmx."""
    mmx = _mod("_mmx")

    class _Cfg:
        def get(self, key, default=None):
            return {"providers": [{"id": "minimax", "api_key": "sk-cp-test-123"}]}.get(key, default)

    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: _Cfg())
    assert mmx.minimax_api_key() == "sk-cp-test-123"


def test_key_empty_when_provider_missing(monkeypatch):
    """Ohne Provider 'minimax' kommt '' zurück – nicht None, nicht ein Fehler."""
    mmx = _mod("_mmx")

    class _Cfg:
        def get(self, key, default=None):
            return {"providers": []}.get(key, default)

    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: _Cfg())
    assert mmx.minimax_api_key() == ""


# --- 2) Key landet als --api-key im Aufruf ------------------------------------

def test_base_cmd_carries_api_key():
    """Der Basisbefehl enthält --api-key <key> und --non-interactive."""
    mmx = _mod("_mmx")
    cmd = mmx.mmx_base_cmd("sk-cp-abc")
    assert "--api-key" in cmd
    assert cmd[cmd.index("--api-key") + 1] == "sk-cp-abc"
    assert "--non-interactive" in cmd


def test_base_cmd_without_key_is_still_valid():
    """Ohne Key bleibt der Befehl gültig (CLI meldet dann selbst den Login-Bedarf)."""
    mmx = _mod("_mmx")
    cmd = mmx.mmx_base_cmd("")
    assert "--api-key" not in cmd
    assert cmd[0] == "mmx"


# --- 3) Fehlender Key → klare Meldung statt API-Fehler ------------------------

@pytest.mark.parametrize("mod_name", ["image", "music", "speech", "video", "vision"])
def test_missing_key_gives_clear_message(monkeypatch, ctx, mod_name):
    """Fehlt der Key, meldet das Werkzeug das klar – es ruft nicht die API."""
    mmx = _mod("_mmx")
    monkeypatch.setattr(mmx, "minimax_api_key", lambda: "")
    monkeypatch.setattr(mmx, "mmx_binary", lambda: "/usr/bin/mmx")

    mod = _mod(mod_name)
    args = {
        "image": {"prompt": "x"},
        "music": {"prompt": "x"},
        "speech": {"text": "x"},
        "video": {"prompt": "x"},
        "vision": {"image": "/tmp/x.png"},
    }[mod_name]
    # monkeypatch wirkt auf das Modul, das _mmx importiert hat → dort patchen.
    monkeypatch.setattr(mod, "minimax_api_key", lambda: "", raising=False)
    res = asyncio.run(mod.TOOL.execute(args, ctx))
    assert res.success is False
    assert "API-Key" in (res.error or "")


# --- 4) Aufrufe bleiben vollständig --------------------------------------------

@pytest.mark.parametrize("mod_name,args", [
    ("image", {"prompt": "x"}),
    ("speech", {"text": "x"}),
    ("video", {"prompt": "x"}),
    ("vision", {"image": "/tmp/x.png"}),
])
def test_tool_passes_key_to_cli(monkeypatch, ctx, mod_name, args):
    """Das Werkzeug ruft mmx mit --api-key auf (Kommandowerk prüfen)."""
    mod = _mod(mod_name)
    seen: dict = {}

    async def _fake_exec(*cmd, **kw):
        seen["cmd"] = list(cmd)
        raise asyncio.TimeoutError  # Abbruch nach dem Aufruf – reicht für die Prüfung

    monkeypatch.setattr(mod.asyncio, "create_subprocess_exec", _fake_exec)
    monkeypatch.setattr(mod, "minimax_api_key", lambda: "sk-cp-xyz", raising=False)
    monkeypatch.setattr(mod, "mmx_binary", lambda: "/usr/bin/mmx", raising=False)

    asyncio.run(mod.TOOL.execute(args, ctx))
    cmd = seen.get("cmd", [])
    assert "--api-key" in cmd
    assert cmd[cmd.index("--api-key") + 1] == "sk-cp-xyz"


def test_music_is_reported_as_unavailable(ctx, monkeypatch):
    """Befund 02.11.2026: mmx hat KEIN 'music'-Kommando, die MiniMax-Musik-API
    ist für Neukunden abgeschaltet. Das Werkzeug muss das klar melden und auf
    das Kern-Werkzeug generate_music verweisen — statt einen API-Fehler zu
    produzieren oder stillzuschweigen.
    """
    mod = _mod("music")
    monkeypatch.setattr(mod, "mmx_binary", lambda: "/usr/bin/mmx", raising=False)
    monkeypatch.setattr(mod, "minimax_api_key", lambda: "sk-cp-xyz", raising=False)
    res = asyncio.run(mod.TOOL.execute({"prompt": "fröhliche Klaviermusik"}, ctx))
    assert res.success is False
    assert "generate_music" in (res.error or "")
    assert "music" in (res.error or "").lower()

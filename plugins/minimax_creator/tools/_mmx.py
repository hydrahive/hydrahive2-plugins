"""Gemeinsame mmx-Hilfe: API-Key aus der Kern-Konfiguration statt aus ~/.mmx.

Befund 02.11.2026: Die mmx-CLI liest ihren Key aus ~/.mmx/config.json. Dort stand
ein alter Key, den die MiniMax-API mit "invalid api key" ablehnt — jedes Creator-
Werkzeug scheiterte deshalb mit:

    mmx exit=1: {"error": {"code": 1, "message": "API error: invalid api key (HTTP 200)"}}

Der Kern hat inzwischen einen gültigen Key in der LLM-Konfiguration
(Provider "minimax"). Genau wie die Kern-Werkzeuge für OpenRouter holen die
Creator-Werkzeuge ihren Key jetzt aus dieser SSOT und reichen ihn per
--api-key an die CLI weiter. Damit gibt es nur noch EINE Quelle für den Key.

Muster (Kern): hydrahive/tools/_openrouter_media.py → openrouter_key() →
hydrahive/llm/_config.py → get_provider_key(load_config(), "openrouter").
"""
from __future__ import annotations

import os
import shutil


def minimax_api_key() -> str:
    """MiniMax-API-Key aus der LLM-Konfiguration des Kerns (leer = keiner)."""
    try:
        from hydrahive.llm._config import get_provider_key, load_config
    except Exception:  # Kern nicht importierbar (z. B. im Plugin-Test) → leer
        return ""
    try:
        return get_provider_key(load_config(), "minimax") or ""
    except Exception:
        return ""


def mmx_binary() -> str | None:
    """Pfad zur mmx-CLI, falls installiert (sonst None)."""
    return shutil.which("mmx")


def mmx_base_cmd(api_key: str) -> list[str]:
    """Grundbefehl für mmx mit Key und nicht-interaktiver Ausgabe.

    Der Key wird ausschließlich über --api-key übergeben, damit er nicht in
    einer Datei landen muss und die CLI nicht erst ein Login verlangt.
    """
    cmd = ["mmx", "--non-interactive"]
    if api_key:
        cmd += ["--api-key", api_key]
    return cmd


def missing_key_message() -> str:
    return (
        "MiniMax-API-Key fehlt. Hinterlege ihn in der LLM-Konfiguration "
        "(Provider 'minimax') — die Werkzeuge lesen ihn von dort."
    )

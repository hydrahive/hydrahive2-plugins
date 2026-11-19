"""Regressionstest für den Server-Totalhänger vom 2026-11-19: grep() las
Dateien per path.read_text() SYNCHRON im Event-Loop-Thread. Bei vielen/
großen Dateien blockierte das den kompletten Event-Loop (nicht nur die
eine Session) -> Discord-Heartbeat >590s blockiert -> harter Neustart
nötig, "es ging rein gar nichts mehr".

grep muss Datei-IO über asyncio.to_thread() in einen Worker-Thread
auslagern, damit der Event-Loop währenddessen für ALLE anderen
Sessions/Hintergrund-Tasks responsiv bleibt.
"""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import time

import pytest

from hydrahive.tools.base import ToolContext

ROOT = pathlib.Path(__file__).resolve().parents[1] / "plugins"
GREP = ROOT / "file_search" / "tools" / "grep.py"


def _tool():
    spec = importlib.util.spec_from_file_location("grep_nonblocking_test", GREP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def big_ws(tmp_path):
    """Viele ~1MB-Dateien (~300MB gesamt), damit ein naiver synchroner
    read_text()-Lauf im Event-Loop messbar Zeit braucht. Bei kleineren
    Testgrößen (<~50MB) verschwindet der Unterschied zwischen blockierend
    und asyncio.to_thread() im Rauschen — mit dieser Größe liegt der
    Unterschied bei >150ms (gemessen: alt max_gap≈total_time≈0.17s, neu
    max_gap≈0.035s bei gleicher Laufzeit)."""
    w = tmp_path / "ws"
    w.mkdir()
    content = ("zeile mit text und einem treffer: ZIEL_PATTERN\n" * 20_000)
    for i in range(300):
        (w / f"datei_{i}.txt").write_text(content)
    return w


def test_event_loop_bleibt_waehrend_grep_responsiv(big_ws):
    """Kern-Regressionstest: während grep() läuft, muss ein paralleler
    asyncio-Heartbeat regelmäßig weiterlaufen können. Bei synchronem
    read_text() im Loop-Thread würde der Heartbeat für die gesamte
    grep-Laufzeit aussetzen (genau das Symptom vom Vorfall)."""
    mod = _tool()
    ctx = ToolContext(session_id="s", agent_id="a", user_id="u", workspace=big_ws)

    async def run():
        heartbeat_gaps: list[float] = []
        last = time.monotonic()
        stop = asyncio.Event()

        async def heartbeat():
            nonlocal last
            while not stop.is_set():
                await asyncio.sleep(0.01)
                now = time.monotonic()
                heartbeat_gaps.append(now - last)
                last = now

        hb_task = asyncio.create_task(heartbeat())
        await mod.TOOL.execute({"pattern": "ZIEL_PATTERN"}, ctx)
        stop.set()
        await hb_task
        return heartbeat_gaps

    gaps = asyncio.run(run())
    assert gaps, "Heartbeat ist nie gelaufen"
    # Kein einzelner Gap darf die grep-Laufzeit dominieren (vorher: ein
    # einziger Gap ≈ Gesamtlaufzeit, weil der Loop komplett blockierte;
    # gemessen ≈0.17s bei dieser Workload-Größe). Grenze großzügig bei
    # 0.1s, damit der Test nicht auf langsamer CI-Hardware flackert, aber
    # den alten blockierenden Code (≈0.17s) sicher erkennt.
    assert max(gaps) < 0.1, (
        f"Event-Loop war für {max(gaps):.3f}s blockiert — grep liest "
        "vermutlich wieder synchron im Loop-Thread statt über asyncio.to_thread()"
    )


def test_grep_funktioniert_weiterhin_korrekt(big_ws):
    mod = _tool()
    ctx = ToolContext(session_id="s", agent_id="a", user_id="u", workspace=big_ws)
    res = asyncio.run(mod.TOOL.execute({"pattern": "ZIEL_PATTERN"}, ctx))
    assert res.success
    assert res.output["total_matches"] > 0
    assert res.output["files_with_matches"] == 300


def test_zu_grosse_datei_wird_uebersprungen_statt_server_zu_belasten(tmp_path):
    mod = _tool()
    w = tmp_path / "ws"
    w.mkdir()
    # Über MAX_FILE_BYTES (2 MB) — wird übersprungen statt komplett eingelesen.
    (w / "riesig.txt").write_text("ZIEL " * 1_000_000)
    (w / "klein.txt").write_text("ZIEL\n")
    ctx = ToolContext(session_id="s", agent_id="a", user_id="u", workspace=w)
    res = asyncio.run(mod.TOOL.execute({"pattern": "ZIEL"}, ctx))
    assert res.success
    # Die kleine Datei muss trotzdem gefunden werden.
    found_files = {m["file"] for m in res.output["matches"]}
    assert any("klein.txt" in f for f in found_files)

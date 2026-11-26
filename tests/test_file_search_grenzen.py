"""file-search 0.4.0: begrenzter Verzeichnis-Lauf (26.11.2026).

Gemessen auf .4 (tool_calls, 30 Tage): find typisch 39 ms, aber bis 16 min; grep bis 41 s. Ursache: rglob/glob
synchron im Event-Loop, durch Netzlaufwerke (mounts/ = CIFS auf das NAS), .git und node_modules, ohne Zeitgrenze.
Gegenprobe: mit find.py/grep.py/tree.py von 0.3.0 werden die Tests zu Mount, Symlink, Zeitgrenze, Event-Loop und
pattern rot.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import pathlib
import time

import pytest

from hydrahive.tools.base import ToolContext

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "plugins" / "file_search" / "tools"


def _mod(name: str):
    spec = importlib.util.spec_from_file_location(f"fs_{name}_grenzen", TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ctx(ws: pathlib.Path) -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=ws)


def _run(name: str, args: dict, ws: pathlib.Path):
    return asyncio.run(_mod(name).TOOL.execute(args, _ctx(ws)))


@pytest.fixture
def ws(tmp_path):
    w = tmp_path / "ws"
    (w / "src" / "tief").mkdir(parents=True)
    (w / "src" / "ziel.py").write_text("ZIEL\n")
    (w / "src" / "tief" / "ziel_tief.py").write_text("ZIEL\n")
    (w / "readme.md").write_text("nix\n")
    for skip in (".git", "node_modules"):
        (w / skip).mkdir()
        (w / skip / "ziel_versteckt.py").write_text("ZIEL\n")
    return w


# --- Symlink-Ordner und Mount-Grenze -------------------------------------------------------------------------------

def test_symlink_ordner_wird_nicht_betreten(ws, tmp_path):
    """Fängt: rglob folgt einem verlinkten Ordner (z. B. auf ein NAS oder den ganzen Server) – lief bis 16 min."""
    fremd = tmp_path / "fremd"
    fremd.mkdir()
    (fremd / "ziel_fremd.py").write_text("ZIEL\n")
    os.symlink(fremd, ws / "verweis")
    names = {r["name"] for r in _run("find", {"name": "ziel"}, ws).output["results"]}
    assert "ziel_fremd.py" not in names
    grep = _run("grep", {"pattern": "ZIEL"}, ws).output
    assert not any("ziel_fremd" in m["file"] for m in grep["matches"])
    tree = _run("tree", {}, ws).output
    assert "ziel_fremd.py" not in tree["tree"] and "verweis/" in tree["tree"]


def test_anderes_dateisystem_wird_nicht_betreten(ws, monkeypatch):
    """Fängt: der Lauf geht über eine Mount-Grenze (mounts/Hydrahive_backups ist CIFS). Simuliert über st_dev."""
    (ws / "mounts" / "nas").mkdir(parents=True)
    (ws / "mounts" / "nas" / "ziel_nas.py").write_text("ZIEL\n")
    walk = _mod("find")._walk
    echt = os.lstat

    class _St:
        def __init__(self, st):
            self._st = st

        def __getattr__(self, k):
            return 999_999 if k == "st_dev" else getattr(self._st, k)

    def fake_lstat(p, *a, **kw):
        st = echt(p, *a, **kw)
        return _St(st) if str(p).endswith(os.sep + "nas") else st

    monkeypatch.setattr(pathlib.Path, "lstat", lambda self: fake_lstat(self))
    res = walk.walk(ws)
    assert not any(f.name == "ziel_nas.py" for f in res.files)
    assert "mounts/nas" in res.skipped_mounts


def test_versteckte_und_abhaengigkeits_ordner_werden_uebersprungen(ws):
    names = {r["name"] for r in _run("find", {"name": "ziel"}, ws).output["results"]}
    assert names == {"ziel.py", "ziel_tief.py"}


# --- Grenzen -------------------------------------------------------------------------------------------------------

def test_zeitgrenze_bricht_ab_und_meldet_es(tmp_path):
    """Fängt: kein Abbruch – ein riesiger Baum läuft beliebig lange."""
    w = tmp_path / "gross"
    for i in range(30):
        (w / f"d{i}").mkdir(parents=True)
        for j in range(30):
            (w / f"d{i}" / f"f{j}.txt").write_text("x")
    walk = _mod("find")._walk
    res = walk.walk(w, time_budget=0.0)
    assert res.stopped == "Zeitgrenze"
    assert len(res.files) < 900
    res = walk.walk(w, max_entries=50)
    assert res.stopped == "Eintragsgrenze"
    assert walk.walk(w).stopped is None and len(walk.walk(w).files) == 900


def test_find_meldet_unvollstaendiges_ergebnis(ws, monkeypatch):
    mod = _mod("find")
    orig = mod._walk.walk
    monkeypatch.setattr(mod._walk, "walk", lambda root, **kw: orig(root, **{**kw, "time_budget": 0.0}))
    out = asyncio.run(mod.TOOL.execute({"name": "ziel"}, _ctx(ws))).output
    assert "stopped" in out and "unvollständig" in out["stopped"]


def test_max_depth_gilt_wie_bisher(ws):
    """Datei direkt im Ordner = Tiefe 1 (wie len(rel.parts) in 0.3.0)."""
    names = {r["name"] for r in _run("find", {"name": "ziel", "max_depth": 2}, ws).output["results"]}
    assert names == {"ziel.py"}
    names = {r["name"] for r in _run("find", {"name": "ziel", "max_depth": 3}, ws).output["results"]}
    assert names == {"ziel.py", "ziel_tief.py"}


def test_find_nur_mit_pattern_liefert_nicht_alles(ws):
    """Fängt den alten Fehler: ohne 'name' passte '' in jedem Dateinamen – pattern wurde praktisch ignoriert."""
    names = {r["name"] for r in _run("find", {"pattern": "*.md"}, ws).output["results"]}
    assert names == {"readme.md"}


def test_total_found_zaehlt_vor_dem_limit(ws):
    out = _run("find", {"name": "ziel", "limit": 1}, ws).output
    assert out["shown"] == 1 and out["total_found"] == 2


# --- Event-Loop ----------------------------------------------------------------------------------------------------

def test_find_blockiert_den_event_loop_nicht(tmp_path):
    """Fängt: rglob synchron im Loop-Thread (wie grep vor 0.3.0, Vorfall 19.11.)."""
    w = tmp_path / "viel"
    for i in range(200):
        (w / f"d{i}").mkdir(parents=True)
        for j in range(100):
            (w / f"d{i}" / f"f{j}.txt").touch()
    mod = _mod("find")

    async def run():
        gaps, last, stop = [], time.monotonic(), asyncio.Event()

        async def heartbeat():
            nonlocal last
            while not stop.is_set():
                await asyncio.sleep(0.005)
                now = time.monotonic()
                gaps.append(now - last)
                last = now

        hb = asyncio.create_task(heartbeat())
        t = time.monotonic()
        await mod.TOOL.execute({"name": "f1"}, _ctx(w))
        dauer = time.monotonic() - t
        stop.set()
        await hb
        return gaps, dauer

    gaps, dauer = asyncio.run(run())
    assert dauer > 0.05, "Testbaum zu klein, um ein Blockieren zu messen"
    assert max(gaps) < dauer * 0.6, f"Event-Loop {max(gaps):.3f}s blockiert bei {dauer:.3f}s Laufzeit"

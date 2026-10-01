"""Plugin-Werkzeuge bleiben im Arbeitsordner der Session (01.10.2026).

Befund aus dem Mehr-Spezialisten-Lauf: file-search find löste relative Pfade
gegen das Arbeitsverzeichnis des Servers (/opt/hydrahive2) auf statt gegen
ctx.workspace, und absolute Pfade wurden ohne Grenze akzeptiert (Task
3bd963b2 d). Jetzt nutzen alle Werkzeuge safe_path wie file_read/file_write.
"""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import subprocess

import pytest

from hydrahive.tools.base import ToolContext

ROOT = pathlib.Path(__file__).resolve().parents[1] / "plugins"
CASES = [
    ("file_search/tools/find.py", {"name": "a.txt"}),
    ("file_search/tools/grep.py", {"pattern": "hallo"}),
    ("file_search/tools/tree.py", {}),
    ("code_metrics/tools/loc.py", {}),
    ("code_metrics/tools/files.py", {}),
    ("code_metrics/tools/languages.py", {}),
    ("code_metrics/tools/complexity.py", {}),
    ("git_stats/tools/commits.py", {}),
    ("git_stats/tools/authors.py", {}),
    ("git_stats/tools/files.py", {}),
    ("git_stats/tools/diff.py", {}),
]


def _tool(rel: str):
    spec = importlib.util.spec_from_file_location(rel.replace("/", "_")[:-3], ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TOOL


@pytest.fixture
def ws(tmp_path):
    w = tmp_path / "ws"
    (w / "sub").mkdir(parents=True)
    (w / "sub" / "a.txt").write_text("hallo\n")
    (w / "sub" / "b.py").write_text("print('x')\n")
    subprocess.run(["git", "init", "-q", str(w)], check=True)
    subprocess.run(["git", "-C", str(w), "-c", "user.email=t@t", "-c", "user.name=t",
                    "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(w), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    return w


def _run(rel, args, ws):
    ctx = ToolContext(session_id="s", agent_id="a", user_id="u", workspace=ws)
    return asyncio.run(_tool(rel).execute(args, ctx))


@pytest.mark.parametrize("rel,args", CASES)
def test_absoluter_pfad_ausserhalb_wird_abgelehnt(rel, args, ws):
    res = _run(rel, {**args, "path": "/etc"}, ws)
    assert not res.success
    assert "außerhalb" in (res.error or "")


@pytest.mark.parametrize("rel,args", CASES)
def test_ausbruch_per_punkt_punkt_wird_abgelehnt(rel, args, ws):
    res = _run(rel, {**args, "path": "../../"}, ws)
    assert not res.success


@pytest.mark.parametrize("rel,args", CASES)
def test_relativer_pfad_gilt_im_arbeitsordner(rel, args, ws, monkeypatch):
    monkeypatch.chdir("/")  # Server-Arbeitsverzeichnis darf keine Rolle spielen
    res = _run(rel, {**args, "path": "." if rel.startswith("git_stats") else "sub"}, ws)
    assert res.success, res.error


def test_find_findet_datei_relativ(ws, monkeypatch):
    monkeypatch.chdir("/")
    res = _run("file_search/tools/find.py", {"name": "a.txt", "path": "sub"}, ws)
    assert res.success and "a.txt" in str(res.output)

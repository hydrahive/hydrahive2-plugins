"""Gemeinsamer, begrenzter Verzeichnis-Lauf für find/grep/tree (0.4.0).

Gemessen 26.11.2026 (tool_calls, .4): find brauchte typisch 39 ms, aber bis 16 min. Ursache: ``root.rglob("*")``
lief synchron im Event-Loop, folgte Netzlaufwerken (z. B. ``mounts/`` mit CIFS auf das NAS) und baute erst die
komplette Liste, bevor gefiltert wurde (auch ``.git`` und ``node_modules`` wurden vollständig gelesen).

Jetzt:
- ``os.walk`` mit sofortigem Beschneiden: versteckte Ordner, bekannte Bau-/Abhängigkeitsordner, Ordner auf einem
  anderen Dateisystem (Mount-Grenze, ``st_dev``) und Symlink-Ordner werden gar nicht erst betreten.
- Harte Grenzen: höchstens ``max_entries`` Einträge und ``time_budget`` Sekunden; danach Abbruch mit Vermerk.
- Läuft per ``asyncio.to_thread`` im Worker-Thread, nie im Event-Loop (Vorfall 19.11.: grep blockierte den Server).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = frozenset({
    "node_modules", "__pycache__", "venv", ".venv", "dist", "build", "target", ".next", ".git", ".idea", ".vscode",
})
MAX_ENTRIES = 200_000      # Verzeichniseinträge (Dateien + Ordner), danach Abbruch
TIME_BUDGET = 20.0         # Sekunden, danach Abbruch


@dataclass
class WalkResult:
    files: list[Path] = field(default_factory=list)
    dirs: int = 0
    stopped: str | None = None          # None | "Zeitgrenze" | "Eintragsgrenze"
    skipped_mounts: list[str] = field(default_factory=list)


def walk(root: Path, *, max_depth: int = 10, extra_skip: frozenset[str] | set[str] = frozenset(),
         max_entries: int = MAX_ENTRIES, time_budget: float = TIME_BUDGET, keep=None) -> WalkResult:
    """Dateien unter ``root`` (ohne versteckte/übersprungene Ordner, nicht über Mount-Grenzen, keine Symlink-Ordner).

    ``keep(path) -> bool`` filtert Dateien schon während des Laufs (spart Speicher bei großen Bäumen).
    ``max_depth`` zählt Ordner-Ebenen unter ``root`` (Datei direkt in root = Tiefe 1, wie bisher ``len(rel.parts)``).
    """
    res = WalkResult()
    skip = SKIP_DIRS | set(extra_skip)
    deadline = time.monotonic() + time_budget
    try:
        root_dev = root.stat().st_dev
    except OSError:
        return res
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        depth = len(here.relative_to(root).parts)
        kept_dirs = []
        for d in sorted(dirnames):
            if d.startswith(".") or d in skip:
                continue
            p = here / d
            try:
                st = p.lstat()
            except OSError:
                continue
            if os.path.islink(p):
                continue
            if st.st_dev != root_dev:
                res.skipped_mounts.append(str(p.relative_to(root)))
                continue
            kept_dirs.append(d)
        dirnames[:] = kept_dirs if depth + 1 < max_depth else []
        res.dirs += len(kept_dirs)
        for name in filenames:
            if depth + 1 > max_depth:
                break
            p = here / name
            if keep is None or keep(p):
                res.files.append(p)
        seen += len(dirnames) + len(filenames)
        if seen >= max_entries:
            res.stopped = "Eintragsgrenze"
            break
        if time.monotonic() > deadline:
            res.stopped = "Zeitgrenze"
            break
    return res


def is_skipped_path(root: Path, path: Path, extra_skip: frozenset[str] | set[str] = frozenset()) -> bool:
    """True, wenn ein Pfadteil unter ``root`` versteckt ist oder übersprungen wird (für tree's Einzel-Ebenen)."""
    skip = SKIP_DIRS | set(extra_skip)
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(p.startswith(".") or p in skip for p in parts)

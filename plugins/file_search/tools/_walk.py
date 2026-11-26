"""Gemeinsamer, begrenzter Verzeichnis-Lauf für find/grep/tree (0.4.0).

Gemessen 26.11.2026 (tool_calls, .4): find brauchte typisch 39 ms, aber bis 16 min. Ursache: ``root.rglob("*")``
lief synchron im Event-Loop, folgte Netzlaufwerken (z. B. ``mounts/`` mit CIFS auf das NAS) und baute erst die
komplette Liste, bevor gefiltert wurde (auch ``.git`` und ``node_modules`` wurden vollständig gelesen).

Jetzt:
- ``os.walk`` mit sofortigem Beschneiden: versteckte Ordner, bekannte Bau-/Abhängigkeitsordner, Ordner auf einem
  anderen Dateisystem (Mount-Grenze, ``st_dev``) und Symlink-Ordner werden gar nicht erst betreten.
- Harte Grenzen: höchstens ``max_entries`` Einträge und ``time_budget`` Sekunden; danach Abbruch mit Vermerk.
- Mount-Grenze per ``st_dev``: auch btrfs-Subvolumes und Bind-Mounts eines anderen Dateisystems werden nicht betreten
  (bewusst). Symlink-Ordner (z. B. ``linked/<Projekt>``) werden gemeldet und lassen sich direkt als ``path`` angeben.
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
    skipped_links: list[str] = field(default_factory=list)   # Symlink-Ordner (z. B. linked/<Projekt>)


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
                res.skipped_links.append(str(p.relative_to(root)))
                continue
            if st.st_dev != root_dev:
                res.skipped_mounts.append(str(p.relative_to(root)))
                continue
            kept_dirs.append(d)
        dirnames[:] = kept_dirs if depth + 1 < max_depth else []
        res.dirs += len(kept_dirs)
        seen += len(dirnames)
        for name in filenames:
            if depth + 1 > max_depth:
                break
            seen += 1
            if seen % 1000 == 0 and (seen >= max_entries or time.monotonic() > deadline):
                break                            # Grenzen auch in einem einzelnen sehr großen Ordner
            # Versteckte DATEIEN wie Ordner überspringen (.env, .npmrc, .pgpass, .git-credentials): grep gäbe sonst
            # Geheimnisse als Tool-Ausgabe zurück (Review #7, „muss“; 0.3.0 prüfte jeden Pfadteil).
            if name.startswith("."):
                continue
            p = here / name
            if keep is None or keep(p):
                res.files.append(p)
        if seen >= max_entries:
            res.stopped = "Eintragsgrenze"
            break
        if time.monotonic() > deadline:
            res.stopped = "Zeitgrenze"
            break
    return res


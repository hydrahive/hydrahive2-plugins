# git-stats Plugin

Git-Analytics für HydraHive2 Agenten.

## Tools

### `git_commits`
Zeigt die letzten N Commits eines Git-Repos.

```yaml
path: /path/to/repo   # optional, default: workspace
limit: 10             # optional, default: 10, max: 100
```

### `git_authors`
Zeigt alle Autoren mit Commit-Count, sortiert nach Aktivität.

```yaml
path: /path/to/repo   # optional, default: workspace
```

### `git_files`
Zeigt Dateien mit Änderungsstatistik (Lines Added/Deleted).

```yaml
path: /path/to/repo   # optional, default: workspace
pattern: "*.py"       # optional, filter by path
```

### `git_diff`
Zeigt Diff zwischen Commits oder Branches.

```yaml
path: /path/to/repo   # optional, default: workspace
ref: HEAD            # optional, default: HEAD
ref2: main          # optional, compare ref vs ref2
file: src/main.py   # optional, only this file
```

## Installation

Das Plugin wird automatisch über den PluginHub geladen.
Lokal: `cp -r git_stats ~/.hh2-dev/data/plugins/`

## Beispiel-Nutzung im Chat

```
Zeig mir die letzten 5 Commits im hydrahive2 Repo

Wer hat am meisten in diesem Repo beigetragen?

Welche Python-Dateien wurden am häufigsten geändert?

Zeig mir den Diff zwischen main und feature-branch
```

# code-metrics Plugin

Code-Analyse für HydraHive2 Agenten.

## Tools

### `loc` (Lines of Code)
Zählt Lines of Code nach Dateityp.

```yaml
path: /path/to/project   # optional
extensions: ["py", "js"] # optional
```

### `languages`
Zeigt Sprachen-Verteilung mit Prozent.

```yaml
path: /path/to/project   # optional
```

### `files`
Listet alle Dateien mit Größen.

```yaml
path: /path/to/project   # optional
sort_by: size           # size, name, modified
limit: 100              # max files
```

### `complexity`
Analysiert Complexity-Indikatoren.

```yaml
path: /path/to/project   # optional
extensions: [".py"]       # optional
max_lines: 200          # max lines per file
```

## Beispiel-Nutzung

```
Wie viele Zeilen Python-Code hat das Projekt?

Welche Sprache wird am meisten verwendet?

Zeig mir die größten Dateien im Projekt.

Welche Dateien haben die meisten TODOs?
```

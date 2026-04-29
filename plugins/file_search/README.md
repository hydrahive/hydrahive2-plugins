# file-search Plugin

Erweiterte Dateisuche für HydraHive2 Agenten.

## Tools

### `grep`
Durchsucht Dateien nach Regex-Pattern.

```yaml
path: /path/to/project
pattern: "def main"
extensions: ["py"]
context: 2
```

### `find`
Findet Dateien nach Name.

```yaml
path: /path/to/project
name: "config"
extensions: ["json", "yaml"]
sort_by: modified
```

### `tree`
Zeigt Verzeichnis-Struktur als Baum.

```yaml
path: /path/to/project
max_depth: 3
show_files: true
extensions: ["py", "js"]
```

## Beispiel-Nutzung

```
Finde alle TODO-Kommentare in Python-Dateien.

Suche nach 'async def' im Projekt.

Welche Config-Dateien gibt es?

Zeig mir die Projektstruktur als Baum.
```

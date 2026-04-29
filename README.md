# HydraHive2 Plugin-Hub

Zentraler Plugin-Marketplace für HydraHive2. Jedes Verzeichnis unter `plugins/`
ist ein eigenständiges Plugin. `hub.json` ist der maschinenlesbare Index, den
HydraHive lädt, wenn der Benutzer in der Admin-UI auf "Plugins → Hub" geht.

## Aufbau

```
plugins/
├── hello-world/        Demo-Plugin (Referenz)
└── ...
```

Jedes Plugin hat eine `plugin.yaml` als Manifest und mindestens ein Python-
Modul mit einer `on_load(ctx)`-Funktion.

## Plugin schreiben

Siehe [docs/PLUGIN_AUTHORING.md](docs/PLUGIN_AUTHORING.md).

## Lokal testen

Plugin-Verzeichnis nach `$HH_DATA_DIR/plugins/<name>/` kopieren oder symlinken,
HydraHive2-Service neustarten. Im Dev-Mode liegt das unter `~/.hh2-dev/data/plugins/`.

## Lizenz

Die Plugin-API selbst ist Teil von HydraHive2 (siehe Haupt-Repo). Einzelne
Plugins in diesem Hub können eigene Lizenzen mitbringen — siehe `plugin.yaml`.

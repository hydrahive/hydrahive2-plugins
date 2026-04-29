# Plugin schreiben für HydraHive2

Ein Plugin ist ein Python-Paket mit einem `plugin.yaml`-Manifest und einer
`on_load(ctx)`-Funktion im Entry-Modul. HydraHive2 entdeckt Plugins beim Start
über das Verzeichnis `$HH_DATA_DIR/plugins/`.

## Mindest-Layout

```
plugins/dein-plugin/
├── plugin.yaml          Manifest (Pflicht)
├── __init__.py          Entry-Modul mit on_load(ctx)
└── tools/
    └── mein_tool.py     Optional — Tool-Implementierung
```

## plugin.yaml

```yaml
name: dein-plugin                # eindeutig, klein-mit-bindestrichen
version: 0.1.0                   # SemVer
description: Was dein Plugin tut.
author: Dein Name
requires_core: ">=2.0.0"         # gegen welche Core-Version gebaut
entry: __init__                  # Modul mit on_load() — Default __init__
permissions:                     # Selbstdeklaration, im MVP informativ
  - tools.register
```

## Entry-Modul

```python
from dein_plugin.tools.mein_tool import TOOL as MEIN_TOOL


def on_load(ctx) -> None:
    ctx.register_tool(MEIN_TOOL)
    ctx.logger.info("mein Plugin bereit")
```

`ctx` ist ein `PluginContext` mit:

- `ctx.plugin_name` — Name aus plugin.yaml
- `ctx.plugin_dir` — Pfad zum Plugin-Verzeichnis (für Asset-Lookup)
- `ctx.logger` — vor-konfigurierter Logger `plugins.<name>`
- `ctx.register_tool(tool)` — Tool dem Core verfügbar machen

## Tools

Ein Tool ist ein `Tool`-Objekt aus `hydrahive.tools.base`:

```python
from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult.ok("hallo")


TOOL = Tool(
    name="mein_tool",
    description="Was es tut.",
    schema={"type": "object", "properties": {}},
    execute=_execute,
)
```

Im Agent erscheint das Tool als `plugin__<plugin-name>__<tool-name>`.

## Tool-Namespace

Plugin-Tools laufen unter `plugin__<plugin>__<tool>`. Damit kollidieren sie
nie mit Core-Tools oder MCP-Tools. Die Agent-Konfiguration referenziert den
voll qualifizierten Namen.

## Was du nicht tun solltest

- Kein Code im Top-Level deines Entry-Moduls, der Seiteneffekte hat. Alles
  in `on_load(ctx)`.
- Keine Imports aus `hydrahive.api` oder `hydrahive.runner` — Plugins arbeiten
  über die Plugin-API, nicht direkt im Core.
- Keine eigenen Threads / Background-Tasks im MVP — kommt später als Hook.

## Plugin testen lokal

```bash
cp -r dein-plugin ~/.hh2-dev/data/plugins/
systemctl --user restart hydrahive2-dev
journalctl --user -u hydrahive2-dev -f | grep dein-plugin
```

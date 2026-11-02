# minimax-creator Plugin

**⚠️ NUR FÜR MINIMAX-AGENTEN! ⚠️**

MiniMax AI Creator Tools für HydraHive2 Agenten mit mmx CLI.

## Voraussetzungen

- **MiniMax-API-Key in der LLM-Konfiguration** (Provider `minimax`) — das ist die
  einzige Quelle. Die Werkzeuge lesen den Key von dort und reichen ihn per
  `--api-key` an die CLI weiter.
- mmx CLI installiert (`npm install -g mmx-cli`)
- Nur für Agenten, die MiniMax als Backend nutzen

> **Geändert in 0.2.0 (02.11.2026):** Vorher las die mmx-CLI ihren Key aus
> `~/.mmx/config.json`. Dort stand ein alter Key, den die API mit
> „invalid api key" ablehnte — jedes Werkzeug scheiterte. Jetzt kommt der Key
> aus der LLM-Konfiguration, wie es die Kern-Werkzeuge für OpenRouter auch tun.

## Tools

### `image`
Generiert Bilder mit MiniMax AI.

```yaml
prompt: "Ein süßer Hund auf einem Schlitten"
aspect_ratio: "1:1"  # 1:1, 16:9, 9:16, 4:3, 3:4
```

### `video`
Generiert Videos mit MiniMax AI (dauert je nach Länge mehrere Minuten).

```yaml
prompt: "Ein Hund rennt durch Schnee"
```

### `speech`
Text-to-Speech mit MiniMax AI.

```yaml
text: "Hallo, ich bin ein HydraHive Agent!"
voice: "German_FriendlyMan"   # optional; 332 Stimmen, davon 3 deutsche
speed: 1.0                    # optional, 0.5–2.0
```

### `vision`
Analysiert Bilder mit MiniMax Vision AI.

```yaml
image: "/pfad/zum/bild.jpg"
prompt: "Was ist auf dem Bild?"   # optional
```

### `music` — ⚠️ derzeit nicht nutzbar
Der Befund vom 02.11.2026: die mmx-CLI hat **kein `music`-Kommando**
(`mmx --help` listet auth/text/speech/image/video/search/vision/quota/config/
agent/file/update). Zusätzlich ist die MiniMax-Musik-API für Neukunden
abgeschaltet: *„This Music API is no longer available to new users."*

**Bis das geklärt ist: `generate_music` aus dem Kern nutzen** (OpenRouter/Lyria),
das ist der funktionierende Weg.

## Installation

Dieses Plugin ist **automatisch für MiniMax-Agenten** verfügbar.

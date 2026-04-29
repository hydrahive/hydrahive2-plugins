# minimax-creator Plugin

**⚠️ NUR FÜR MINIMAX-AGENTEN! ⚠️**

MiniMax AI Creator Tools für HydraHive2 Agenten mit mmx CLI.

## ⚠️ Voraussetzungen

- MiniMax API Key konfiguriert (`mmx auth login`)
- mmx CLI installiert
- Nur für Agenten die MiniMax als Backend nutzen

## Tools

### `image`
Generiert Bilder mit MiniMax AI.

```yaml
prompt: "Ein süßer Hund auf einem Schlitten"
size: "1:1"  # 1:1, 16:9, 9:16, 4:3
style: "natural"  # natural, anime, realistic
```

### `music`
Generiert Musik mit MiniMax AI.

```yaml
prompt: "Fröhliche Hintergrundmusik mit Klavier"
title: "Fröhlicher Tag"
```

### `video`
Generiert Videos mit MiniMax AI.

```yaml
prompt: "Ein Hund rennt durch Schnee"
duration: 5
```

### `speech`
Text-to-Speech mit MiniMax AI.

```yaml
text: "Hallo, ich bin ein HydraHive Agent!"
voice: "female-young"
speed: 1.0
```

### `vision`
Analysiert Bilder mit MiniMax Vision AI.

```yaml
image: "/path/to/image.jpg"
prompt: "Was ist auf dem Bild?"
```

## Installation

Dieses Plugin ist **automatisch für MiniMax-Agenten** verfügbar.

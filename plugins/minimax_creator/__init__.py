"""MiniMax Creator Plugin — NUR für MiniMax-Agenten!

Tools für Media-Generierung mit MiniMax API:
- Bildgenerierung
- Musikgenerierung
- Videogenerierung
- Sprach-Synthese
- Bild-Analyse (Vision)
"""

from minimax_creator.tools.image import TOOL as IMAGE_TOOL
from minimax_creator.tools.music import TOOL as MUSIC_TOOL
from minimax_creator.tools.video import TOOL as VIDEO_TOOL
from minimax_creator.tools.speech import TOOL as SPEECH_TOOL
from minimax_creator.tools.vision import TOOL as VISION_TOOL


def on_load(ctx) -> None:
    ctx.register_tool(IMAGE_TOOL)
    ctx.register_tool(MUSIC_TOOL)
    ctx.register_tool(VIDEO_TOOL)
    ctx.register_tool(SPEECH_TOOL)
    ctx.register_tool(VISION_TOOL)
    ctx.logger.info("minimax-creator Plugin geladen (NUR MiniMax-Agenten!)")
    ctx.logger.info("  - image: Bilder generieren")
    ctx.logger.info("  - music: Musik generieren")
    ctx.logger.info("  - video: Videos generieren")
    ctx.logger.info("  - speech: Text-to-Speech")
    ctx.logger.info("  - vision: Bild-Analyse")

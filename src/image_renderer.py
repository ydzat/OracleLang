from __future__ import annotations

import base64
import io
import copy
from functools import lru_cache
import logging

from PIL import Image as PILImage

from langbot_plugin.api.entities.builtin.platform import message as platform_message

logger = logging.getLogger(__name__)

MAX_BASE64_SIZE = 150_000  # ~150KB encoded, QQ send timeout threshold
MAX_WIDTH = 600
MAX_HEIGHT = 3000


@lru_cache(maxsize=1)
def _newline_safe_style():
    """Use private fonts; do not monkey-patch Pillow or pillowmd globally."""
    from pillowmd.CustomMarkdownRenderer import DEFAULT_STYLE, MixFont

    class NewlineSafeFont(MixFont):
        def GetSize(self, text):
            # pillowmd measures characters before handling line breaks. Raqm
            # cannot shape CR/LF; the renderer owns their line-height handling.
            if text in ("\n", "\r"):
                return (0, 0)
            return super().GetSize(text)

    style = copy.copy(DEFAULT_STYLE)
    fonts = {}

    def get_font(main_font, size, second_fonts=None):
        source = DEFAULT_STYLE.GetMixFont(main_font, size, second_fonts)
        key = id(source)
        if key not in fonts:
            fonts[key] = NewlineSafeFont(
                source.font_path, source.size,
                layout_engine=source.layout_engine,
                second_fonts=source.seconde_font_paths,
                font_y_correct=source.font_y_correct,
            )
        return fonts[key]

    style.GetMixFont = get_font
    return style


async def markdown_to_message_chain(
    markdown_text: str,
    title: str = "算卦结果",
) -> platform_message.MessageChain:
    """Render Markdown to an image via pillowmd. Raises on failure."""
    try:
        import pillowmd

        result = await pillowmd.MdToImage(
            text=markdown_text,
            title=title,
            style=_newline_safe_style(),
        )

        if not result or not result.image:
            raise RuntimeError("pillowmd returned no image")

        img = result.image

        # Resize if too large (preserve aspect ratio)
        w, h = img.size
        if w > MAX_WIDTH or h > MAX_HEIGHT:
            ratio = min(MAX_WIDTH / w, MAX_HEIGHT / h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, PILImage.LANCZOS)

        # Convert to RGB and compress as JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        for quality in (50, 35, 25):
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            logger.info(f"JPEG quality={quality}: {len(encoded)} bytes base64")
            if len(encoded) <= MAX_BASE64_SIZE:
                return platform_message.MessageChain([
                    platform_message.Image(base64=encoded),
                ])

        raise RuntimeError(
            f"Image too large even at quality=25 ({len(encoded)} bytes base64)"
        )
    except Exception:
        logger.error("Markdown to image rendering failed", exc_info=True)
        raise

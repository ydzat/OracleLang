from __future__ import annotations

import base64
import io
import logging
from typing import Optional

from PIL import Image as PILImage

from langbot_plugin.api.entities.builtin.platform import message as platform_message

logger = logging.getLogger(__name__)

MAX_BASE64_SIZE = 500_000  # ~500KB encoded, stays under QQ send timeout
MAX_WIDTH = 800
MAX_HEIGHT = 4000


async def markdown_to_message_chain(
    markdown_text: str,
    title: str = "算卦结果",
    fallback_text: Optional[str] = None,
) -> platform_message.MessageChain:
    """Render Markdown to an image, falling back to plain text on failure.

    Uses pillowmd for fast Pillow-based rendering (no browser needed).
    Compresses and resizes output to stay under platform send limits.
    Returns a MessageChain with Image(base64=...) on success,
    or Plain(text=...) on failure.
    """
    try:
        import pillowmd

        result = await pillowmd.MdToImage(
            text=markdown_text,
            title=title,
        )

        if result and result.image:
            img = result.image

            # Resize if too large (preserve aspect ratio)
            w, h = img.size
            if w > MAX_WIDTH or h > MAX_HEIGHT:
                ratio = min(MAX_WIDTH / w, MAX_HEIGHT / h)
                new_size = (int(w * ratio), int(h * ratio))
                img = img.resize(new_size, PILImage.LANCZOS)

            # Convert to RGB and compress as JPEG for smaller output
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            for quality in (75, 60, 40):
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=quality)
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                if len(encoded) <= MAX_BASE64_SIZE:
                    return platform_message.MessageChain([
                        platform_message.Image(base64=encoded),
                    ])

            logger.warning(
                f"Image too large even at quality=40 "
                f"({len(encoded)} bytes base64), falling back to text"
            )
    except Exception:
        logger.warning(
            "Markdown to image rendering failed, using plain text",
            exc_info=True,
        )

    # Fallback: send as plain text
    return platform_message.MessageChain([
        platform_message.Plain(text=fallback_text or markdown_text),
    ])

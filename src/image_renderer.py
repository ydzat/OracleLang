from __future__ import annotations

import base64
import io
import logging
from typing import Optional

from langbot_plugin.api.entities.builtin.platform import message as platform_message

logger = logging.getLogger(__name__)


async def markdown_to_message_chain(
    markdown_text: str,
    title: str = "算卦结果",
    fallback_text: Optional[str] = None,
) -> platform_message.MessageChain:
    """Render Markdown to an image, falling back to plain text on failure.

    Uses pillowmd for fast Pillow-based rendering (no browser needed).
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
            buffer = io.BytesIO()
            result.image.save(buffer, format="PNG")
            base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return platform_message.MessageChain([
                platform_message.Image(base64=base64_image),
            ])
    except Exception:
        logger.warning("Markdown to image rendering failed, using plain text", exc_info=True)

    # Fallback: send as plain text
    return platform_message.MessageChain([
        platform_message.Plain(text=fallback_text or markdown_text),
    ])

from __future__ import annotations

import base64
import io
import logging

from PIL import Image as PILImage

from langbot_plugin.api.entities.builtin.platform import message as platform_message

logger = logging.getLogger(__name__)

MAX_BASE64_SIZE = 150_000  # ~150KB encoded, QQ send timeout threshold
MAX_WIDTH = 600
MAX_HEIGHT = 3000


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

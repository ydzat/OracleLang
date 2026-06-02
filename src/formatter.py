"""
OracleLang Markdown Formatter
Formats divination results as clean Markdown for output.
Pure Markdown compatible with markdown2img image rendering.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .glyphs import HexagramRenderer


class MarkdownFormatter:
    """
    Formats divination results as Markdown strings.
    Produces platform-compatible Markdown with code blocks and bullet lists.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize formatter with optional logger"""
        self.logger = logger or logging.getLogger(__name__)
        self._renderer = HexagramRenderer(logger=self.logger)

    def format_divination_result(
        self,
        result: Dict[str, Any],
        question: str,
        style: str,
        hexagram_data: Optional[Dict[str, Any]] = None,
        remaining: int = 0,
        daily_max: int = 3,
    ) -> str:
        """
        Format divination result as a complete Markdown string.

        Args:
            result: Interpretation result dict from HexagramInterpreter.interpret()
            question: The user's question string
            style: Display style ("simple", "traditional", "detailed")
            hexagram_data: Optional hexagram data from calculator (for glyph rendering)
            remaining: Remaining daily divination count
            daily_max: Maximum daily divination count

        Returns:
            Formatted Markdown string
        """
        # Extract fields from result dict
        original = result.get("original", {})
        changed = result.get("changed", {})
        moving_lines_meaning: List[str] = result.get("moving_lines_meaning", [])
        overall_meaning = result.get("overall_meaning", "")
        fortune = result.get("fortune", "")
        advice = result.get("advice", "")

        # Determine if there are any moving lines
        has_moving = any(line.strip() for line in moving_lines_meaning if line)

        # Escape user-provided question text
        display_question = self._escape_markdown(question) if question else "随缘一卦"

        # Build the Markdown output section by section
        parts: List[str] = []

        # ── Title ──
        parts.append("# 算卦结果")
        parts.append("")

        # ── Question ──
        parts.append(f"**问题**: {display_question}")
        parts.append("")

        # ── Hexagram visual ──
        parts.append("## 卦象")
        parts.append("")
        parts.append("```")
        parts.append(self._render_hexagram(original, changed, moving_lines_meaning, style, hexagram_data))
        parts.append("```")
        parts.append("")

        # ── Hexagram name ──
        original_name = original.get("name", "未知")
        changed_name = changed.get("name", "")
        if has_moving and changed_name and changed_name != original_name:
            parts.append(f"**{original_name} → {changed_name}**")
        else:
            parts.append(f"**{original_name}**")
        parts.append("")

        # ── Gua Ci (hexagram judgment text) ──
        gua_ci = original.get("gua_ci", "")
        parts.append("## 卦辞")
        parts.append("")
        parts.append(gua_ci)
        parts.append("")

        # ── Moving lines (conditional) ──
        if has_moving:
            parts.append("## 动爻")
            parts.append("")
            for line in moving_lines_meaning:
                if line:
                    parts.append(f"- {line}")
            parts.append("")

        # ── Overall interpretation ──
        parts.append("## 解读")
        parts.append("")
        parts.append(overall_meaning)
        parts.append("")

        # ── Fortune ──
        parts.append("## 吉凶")
        parts.append("")
        parts.append(f"**{fortune}**")
        parts.append("")

        # ── Advice ──
        parts.append("## 建议")
        parts.append("")
        parts.append(advice)
        parts.append("")

        # ── Remaining daily count ──
        parts.append("## 剩余次数")
        parts.append("")
        parts.append(f"{remaining}/{daily_max}")

        return "\n".join(parts)

    def _render_hexagram(
        self,
        original: Dict[str, Any],
        changed: Dict[str, Any],
        moving_lines_meaning: List[str],
        style: str,
        hexagram_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render hexagram visual.

        When hexagram_data (containing raw 6-yao arrays) is available, delegates
        to HexagramRenderer for a full visual glyph. Otherwise falls back to
        showing hexagram names as a simple text representation.
        """
        if hexagram_data is not None:
            try:
                return self._renderer.render_hexagram(
                    original=hexagram_data["original"],
                    changed=hexagram_data["changed"],
                    moving=hexagram_data["moving"],
                    style=style,
                )
            except Exception as e:
                self.logger.warning(f"Hexagram rendering failed, falling back to name: {e}")

        # Fallback: simple name representation
        original_name = original.get("name", "未知")
        changed_name = changed.get("name", "")
        has_moving = any(line.strip() for line in moving_lines_meaning if line)

        if has_moving and changed_name and changed_name != original_name:
            return f"{original_name} → {changed_name}"
        return original_name

    @staticmethod
    def _escape_markdown(text: str) -> str:
        """
        Escape Markdown special characters in user-provided text.

        Escapes: *, _, `, #
        These characters are backslash-escaped to prevent formatting injection
        when the user's question text contains Markdown syntax.
        """
        chars_to_escape = ["*", "_", "`", "#"]
        result = text
        for char in chars_to_escape:
            result = result.replace(char, "\\" + char)
        return result

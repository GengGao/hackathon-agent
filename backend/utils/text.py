from __future__ import annotations

import re


def strip_context_blocks(text: str) -> str:
    if not text:
        return text
    cleaned = re.sub(r"\[FILE:[^\]]+\][\s\S]*?\[/FILE\]", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[URL_TEXT\][\s\S]*?\[/URL_TEXT\]", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned



from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
import asyncio

from utils.text import strip_context_blocks
from llm import client as llm_client, get_current_model


def _shorten(text: str, limit: int = 220) -> str:
    return (text[: limit - 3] + "...") if len(text) > limit else text


def _build_conversation_snippets(messages: List[Dict[str, Any]], max_messages: int = 20, extraction_results: Optional[Dict[str, Any]] = None) -> List[str]:
    def _get_message_field(msg: Any, key: str, default: str = "") -> str:
        if isinstance(msg, dict):
            return str(msg.get(key, default))
        try:
            return str(msg[key])  # sqlite3.Row supports key access
        except Exception:
            return default

    snippets: List[str] = []

    # If extraction results are available, add structured insights first
    if extraction_results and isinstance(extraction_results, dict):
        # Add key decisions if available
        if "key_decisions" in extraction_results and extraction_results["key_decisions"]:
            snippets.append("📋 **Key Decisions from Analysis:**")
            for decision in extraction_results["key_decisions"][:3]:  # Limit to top 3
                if isinstance(decision, dict) and "decision" in decision:
                    snippets.append(f"  • {decision['decision']}")
            snippets.append("")  # Add spacing

        # Add current blockers if available
        if "current_blockers" in extraction_results and extraction_results["current_blockers"]:
            snippets.append("⚠️ **Current Blockers:**")
            for blocker in extraction_results["current_blockers"][:2]:  # Limit to top 2
                if isinstance(blocker, dict) and "blocker" in blocker:
                    snippets.append(f"  • {blocker['blocker']}")
            snippets.append("")  # Add spacing

        # Add technologies chosen if available
        if "technologies_chosen" in extraction_results and extraction_results["technologies_chosen"]:
            snippets.append("🛠️ **Technologies Chosen:**")
            tech_list = []
            for tech in extraction_results["technologies_chosen"][:5]:  # Limit to top 5
                if isinstance(tech, dict) and "text" in tech:
                    tech_list.append(tech["text"])
            if tech_list:
                snippets.append(f"  • {', '.join(tech_list)}")
                snippets.append("")  # Add spacing

    # Add recent conversation messages
    snippets.append("💬 **Recent Conversation:**")
    for msg in messages[-max_messages:]:
        role = _get_message_field(msg, "role", "user")
        raw_content = _get_message_field(msg, "content", "").strip()
        content = _shorten(strip_context_blocks(raw_content))
        if not content:
            continue
        snippets.append(f"- {role}: {content}")

    return snippets


def _can_call_llm_sync() -> bool:
    try:
        loop = asyncio.get_running_loop()
        if loop and loop.is_running():
            return False
    except RuntimeError:
        # No running loop
        return True
    return True


def _ask_llm_once(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 512,
    on_delta: Optional[Callable[[str], None]] = None,
    seed_messages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    if not _can_call_llm_sync():
        return ""

    async def _go() -> str:
        final_parts: List[str] = []
        stream = await llm_client.chat.completions.create(
            model=get_current_model(),
            messages=(seed_messages if seed_messages else [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            try:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None) or getattr(choice, "message", None) or choice
                text = None
                if delta is not None and hasattr(delta, "content"):
                    text = getattr(delta, "content")
                if text is None and isinstance(delta, dict):
                    text = delta.get("content")
                if text:
                    final_parts.append(text)
                    if on_delta:
                        try:
                            on_delta(text)
                        except Exception:
                            pass
            except Exception:
                continue
        return ("".join(final_parts)).strip()

    try:
        return asyncio.run(_go())
    except Exception:
        return ""


def _ask_llm_once_non_stream(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 512,
    allow_reasoning_fallback: bool = False,
    seed_messages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Best-effort single-shot non-streaming call. Returns empty string on error."""
    if not _can_call_llm_sync():
        return ""

    async def _go() -> str:
        try:
            resp = await llm_client.chat.completions.create(
                model=get_current_model(),
                messages=(seed_messages if seed_messages else [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]),
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                extra_body={"reasoning_effort": "low"}
            )
            try:
                # Prefer assistant message content; optionally fall back to reasoning if allowed
                msg = resp.choices[0].message
                content = ""
                try:
                    content = (getattr(msg, "content", None) or "").strip()
                except Exception:
                    content = ""
                if not content and allow_reasoning_fallback:
                    try:
                        reasoning = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
                        if not reasoning and isinstance(msg, dict):
                            reasoning = msg.get("reasoning") or msg.get("reasoning_content")
                        if reasoning:
                            content = str(reasoning).strip()
                    except Exception:
                        pass

                return content
            except Exception:
                return ""
        except Exception:
            return ""

    try:
        return asyncio.run(_go())
    except Exception:
        return ""


async def ask_llm_stream(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 512,
    seed_messages: Optional[List[Dict[str, Any]]] = None,
) -> AsyncGenerator[str, None]:
    """Async generator yielding content tokens from the LLM.

    Backed by the OpenAI-compatible streaming API exposed by the local client.
    Yields only content deltas; ignores reasoning/tool_calls for simplicity.
    """
    stream = await llm_client.chat.completions.create(
        model=get_current_model(),
        messages=(seed_messages if seed_messages else [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]),
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        extra_body={"reasoning_effort": "medium"}
    )
    async for chunk in stream:
        try:
            choice = chunk.choices[0]
            delta = getattr(choice, "delta", None) or getattr(choice, "message", None) or choice
            text = None
            if delta is not None and hasattr(delta, "content"):
                text = getattr(delta, "content")
            if text is None and isinstance(delta, dict):
                text = delta.get("content")
            if text:
                yield text
        except Exception:
            continue


__all__ = [
    "_build_conversation_snippets",
    "_ask_llm_once",
    "_ask_llm_once_non_stream",
    "ask_llm_stream",
]



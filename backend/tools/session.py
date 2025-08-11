from __future__ import annotations

from typing import Optional, Any, Dict


def get_session_id(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the current chat session id injected by the request pipeline.

    When called within the chat-stream flow, the router supplies the active
    session_id automatically to all tool calls. This function surfaces it to
    the model so it never needs to ask the user.
    """
    return {"ok": True, "session_id": session_id}


__all__ = ["get_session_id"]



from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, Form, Request
from fastapi.responses import JSONResponse

from tools import list_todos, add_todo, clear_todos, update_todo, delete_todo


router = APIRouter()


@router.get("/todos")
def get_todos(detailed: bool = Query(False), session_id: Optional[str] = Query(None)):
    return {"todos": list_todos(detailed=detailed, session_id=session_id)}


@router.post("/todos")
def post_todo(item: str = Form(...), session_id: Optional[str] = Form(None)):
    res = add_todo(item, session_id=session_id)
    return {"ok": res.get("ok", True), "todos": list_todos(session_id=session_id)}


@router.delete("/todos")
def delete_todos(session_id: Optional[str] = Query(None)):
    if not session_id:
        return JSONResponse(status_code=400, content={"error": "session_id is required"})
    res = clear_todos(session_id=session_id)
    return {"ok": res.get("ok", True), "deleted": res.get("deleted", 0)}


@router.put("/todos/{todo_id}")
async def update_todo_route(
    todo_id: int,
    request: Request,
    item: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(None),
    session_id: Optional[str] = Form(None),
):
    # Accept either form-encoded fields or JSON body
    fields: Dict[str, Any] = {}
    if item is not None:
        fields["item"] = item
    if status is not None:
        fields["status"] = status
    if sort_order is not None:
        fields["sort_order"] = sort_order

    if session_id is not None:
        fields["session_id"] = session_id

    if not fields:
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                payload = await request.json()
                if isinstance(payload, dict):
                    for k in ("item", "status", "sort_order", "session_id"):
                        if k in payload and payload[k] is not None:
                            fields[k] = payload[k]
        except Exception:
            pass

    if not fields:
        return JSONResponse(status_code=400, content={"error": "No fields provided"})

    res = update_todo(todo_id, **fields)
    if not res.get("ok"):
        # Differentiate not-found vs. no-op
        return JSONResponse(status_code=404, content={"error": "Todo not found"})
    return {"ok": True}


@router.delete("/todos/{todo_id}")
def delete_todo_route(todo_id: int, session_id: Optional[str] = Query(None)):
    res = delete_todo(todo_id, session_id=session_id)
    if not res.get("ok"):
        return JSONResponse(status_code=404, content={"error": "Todo not found"})
    return {"ok": True}



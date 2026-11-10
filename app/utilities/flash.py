from fastapi import Request
import typing

def flash(request: Request, message: str, type: str = "success") -> None:
    # Reassign (don't append in place) so the session middleware sees the change.
    messages = list(request.session.get("_messages", []))
    messages.append({"message": message, "type": type})
    request.session["_messages"] = messages


def get_flashed_messages(request: Request):
   return request.session.pop("_messages") if "_messages" in request.session else []

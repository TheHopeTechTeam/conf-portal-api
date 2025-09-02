"""
User Context (per-request)
"""
from contextvars import ContextVar, Token
from typing import Optional

from pydantic import BaseModel


user_context_var: ContextVar["UserContext"] = ContextVar("UserContext")


class UserContext(BaseModel):
    """Per-request user information"""

    user_id: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    token: Optional[str] = None
    token_payload: Optional[object] = None
    verified: bool = False


def set_user_context(context: "UserContext") -> Token:
    """
    Set the user context for current request.
    Prefer initializing this once in middleware and mutate thereafter.
    """
    return user_context_var.set(context)


def get_user_context() -> "UserContext":
    """
    Get current request's user context. Middleware should have set it.
    """
    return user_context_var.get()



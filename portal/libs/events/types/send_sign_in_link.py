"""
Send sign-in link event.
"""
from portal.libs.events.base import BaseEvent


class SendSignInLinkEvent(BaseEvent):
    """
    Event for async send sign-in link flow.
    """
    email: str

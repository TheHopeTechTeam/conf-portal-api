import uuid

from portal.libs.contexts.api_context import get_api_context


def get_current_username():
    try:
        return get_api_context().username
    except:
        return "system"


def get_current_id():
    try:
        return get_api_context().user_id
    except:
        return uuid.UUID("00000000-0000-0000-0000-000000000000")

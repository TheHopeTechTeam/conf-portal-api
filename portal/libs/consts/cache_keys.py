"""
Constants for Cache keys
"""
from portal.config import settings


def get_cache_key(key: str) -> str:
    """
    Get Cache key
    :param key:
    :return:
    """
    return f"{settings.APP_NAME}:{key}"


def get_firebase_signed_url_key(image_id: int) -> str:
    """
    Get the Firebase signed URL key
    :param image_id:
    :return:
    """
    return get_cache_key(f"firebase:signed_url:{image_id}")


def get_token_blacklist_key(token_hash: str) -> str:
    """
    Get token blacklist key
    :param token_hash: SHA256 hash of the token
    :return: Token blacklist key
    """
    return get_cache_key(f"token_blacklist:{token_hash}")


def get_refresh_token_blacklist_key(token_hash: str) -> str:
    """
    Get refresh token blacklist key
    :param token_hash: SHA256 hash of the refresh token
    :return: Refresh token blacklist key
    """
    return get_cache_key(f"refresh_token_blacklist:{token_hash}")


def get_token_blacklist_pattern() -> str:
    """
    Get token blacklist pattern for scanning
    :return: Pattern for token blacklist keys
    """
    return get_cache_key("token_blacklist:*")


def get_check_in_token_used_key(jti: str) -> str:
    """
    Get Redis key for used check-in token jti.
    :param jti: JWT ID
    :return: Redis key
    """
    return get_cache_key(f"ticket_check_in_used:{jti}")


def get_refresh_token_blacklist_pattern() -> str:
    """
    Get refresh token blacklist pattern for scanning
    :return: Pattern for refresh token blacklist keys
    """
    return get_cache_key("refresh_token_blacklist:*")


def create_permission_key(user_id: str, permission_code: str = None):
    """
    Get permission key
    :param user_id:
    :param permission_code:
    :return:
    """
    if not permission_code:
        return get_cache_key(f"perm:{user_id}")
    return get_cache_key(f"perm:{user_id}:{permission_code}")


def create_user_role_key(user_id: str):
    """
    Get user role key
    :param user_id:
    :return:
    """
    return get_cache_key(f"role:{user_id}")


class CacheExpiry:
    """
    Cache expiry times in seconds
    """
    HOUR = 3600
    DAY = 86400
    WEEK = 604800
    MONTH = 2592000
    YEAR = 31536000


class CacheKeys:

    def __init__(self, resource: str):
        self._app_name = settings.APP_NAME
        self.resource = resource
        self.attributes = []

    def build(self) -> str:
        """
        Build cache key
        :return:
        """
        return f"{self._app_name}:{self.resource}:{''.join(self.attributes)}"

    def add_attribute(self, attribute: str, separator: str = ":") -> 'CacheKeys':
        """
        add_attribute
        :param attribute:
        :param separator:
        :return:
        """
        self.attributes.extend([attribute, separator])
        return self

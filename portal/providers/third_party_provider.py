"""
ThirdPartyAuthProvider
"""
from fastapi import status
from fastapi.security.utils import get_authorization_scheme_param
from firebase_admin import App

from portal.exceptions.responses import ApiBaseException
from portal.libs.logger import logger
from portal.schemas.auth import FirebaseTokenPayload


class ThirdPartyAuthProvider:
    """ThirdPartyAuthProvider"""

    def __init__(self, scheme: str = "Bearer"):
        self._scheme = scheme.lower()

    def verify_firebase_token(self, token: str, app: App = None) -> FirebaseTokenPayload:
        """

        :param token:
        :param app:
        :return:
        """
        from portal.providers import FirebaseProvider
        firebase_provider = FirebaseProvider(app=app)
        scheme, credentials = get_authorization_scheme_param(token)
        if scheme.lower() != self._scheme:
            raise ApiBaseException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        try:
            return firebase_provider.verify_id_token(id_token=credentials)
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            raise ApiBaseException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

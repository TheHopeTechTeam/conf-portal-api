"""
Handler for authentication
"""
from portal.providers.firebase.base import FirebaseProvider
from portal.schemas.auth import FirebaseTokenPayload


class AuthHandler:
    """AuthHandler"""

    async def verify_firebase_token(
        self,
        token: str
    ) -> FirebaseTokenPayload:
        """

        :param token:
        :return:
        """
        return FirebaseProvider().authentication.verify_id_token(id_token=token)


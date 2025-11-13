"""
FirebaseProvider
"""
from firebase_admin import auth, App
from firebase_admin.auth import UserRecord

from portal.schemas.auth import FirebaseTokenPayload
from .authentication import FirebaseAuthentication


class FirebaseProvider:
    """FirebaseProvider"""

    def __init__(self, app: App = None):
        """initialize"""
        self.app = app

    @property
    def authentication(self) -> FirebaseAuthentication:
        """
        authentication
        """
        return FirebaseAuthentication(app=self.app)

    def verify_id_token(
        self,
        id_token: str,
        check_revoked: bool = False,
        clock_skew_seconds: int = 0
    ) -> FirebaseTokenPayload:
        """
        Verify id token
        :param id_token:
        :param check_revoked:
        :param clock_skew_seconds:
        :return:
        """
        payload = auth.verify_id_token(
            id_token=id_token,
            app=self.app,
            check_revoked=check_revoked,
            clock_skew_seconds=clock_skew_seconds
        )
        return FirebaseTokenPayload(**payload)

    def get_user(self, uid: str) -> UserRecord:
        """
        Get user
        """
        return auth.get_user(uid=uid, app=self.app)


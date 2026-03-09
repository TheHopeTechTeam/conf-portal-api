"""
FirebaseProvider
"""
from firebase_admin import auth, App
from firebase_admin.auth import ActionCodeSettings, UserRecord

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

    def generate_sign_in_with_email_link(
        self,
        email: str,
        continue_url: str,
        handle_code_in_app: bool = True
    ) -> str:
        """
        Generate sign-in link for email link authentication.
        Used for custom email templates; send the returned link via your own email.
        :param email: Recipient email address.
        :param continue_url: URL to redirect after user clicks the link (must be in Authorized domains).
        :param handle_code_in_app: Whether the link is opened in app or web first.
        :return: The sign-in link URL to embed in your email.
        """
        action_code_settings = ActionCodeSettings(
            url=continue_url,
            handle_code_in_app=handle_code_in_app,
        )
        return auth.generate_sign_in_with_email_link(
            email=email,
            action_code_settings=action_code_settings,
            app=self.app,
        )


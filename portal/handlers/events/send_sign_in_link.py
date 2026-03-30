"""
Send sign-in link event handler.
"""
from urllib.parse import quote, urlparse

from portal.config import settings
from portal.handlers.ticket import TicketHandler
from portal.handlers.user import UserHandler
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.events.base import EventHandler
from portal.libs.events.types import SendSignInLinkEvent
from portal.libs.logger import logger
from portal.models import PortalUserProfile
from portal.providers.firebase.base import FirebaseProvider
from portal.providers.login_verification_email_provider import LoginVerificationEmailProvider
from portal.libs.database import Session


def _is_local_conference_frontend_url(url: str | None) -> bool:
    """
    True when CONFERENCE_FRONTEND_URL host is loopback (dev web test flow path).
    """
    if not url or not str(url).strip():
        return False
    hostname = (urlparse(str(url).strip()).hostname or "").lower()
    return hostname in ("localhost", "127.0.0.1", "::1")


class SendSignInLinkEventHandler(EventHandler):
    """
    Handle async send sign-in link flow.
    """

    def __init__(
        self,
        session: Session,
        user_handler: UserHandler,
        ticket_handler: TicketHandler,
        firebase_provider: FirebaseProvider,
        login_verification_email_provider: LoginVerificationEmailProvider,
    ):
        self._session = session
        self._user_handler = user_handler
        self._ticket_handler = ticket_handler
        self._firebase_provider = firebase_provider
        self._login_verification_email_provider = login_verification_email_provider

    @property
    def event_type(self) -> type[SendSignInLinkEvent]:
        return SendSignInLinkEvent

    @distributed_trace()
    async def handle(self, event: SendSignInLinkEvent) -> None:
        user_id = await self._user_handler.ensure_portal_user_and_profile_by_email(email=event.email)
        await self._ticket_handler.sync_user_ticket(user_id=user_id, email=event.email)
        display_name = await (
            self._session.select(PortalUserProfile.display_name)
            .where(PortalUserProfile.user_id == user_id)
            .fetchval()
        )
        member_name = display_name.strip() if display_name and display_name.strip() else event.email

        continue_url = f"{settings.CONFERENCE_FRONTEND_URL.rstrip('/')}/finishSignIn"
        try:
            raw_link = self._firebase_provider.generate_sign_in_with_email_link(
                email=event.email,
                continue_url=continue_url,
            )
            base_url = settings.CONFERENCE_FRONTEND_URL.rstrip("/")
            if _is_local_conference_frontend_url(settings.CONFERENCE_FRONTEND_URL):
                link_path = "/dev/email-link-callback"
            else:
                link_path = "/__/auth/links"
            sign_in_link = f"{base_url}{link_path}?link={quote(raw_link, safe='')}"
            await self._login_verification_email_provider.send_login_verification_email(
                to_email=event.email,
                sign_in_link=sign_in_link,
                member_name=member_name,
            )
        except Exception as exc:
            logger.error(
                "Failed to process send sign-in link event for %s: %s",
                event.email,
                exc,
                exc_info=True,
            )

"""
LoginVerificationEmailProvider

Sends login verification (sign-in link) email using a custom HTML template and SMTP.
"""
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.smtp_client.smtp_client import SmtpClient


LOGIN_VERIFICATION_EMAIL_SUBJECT = "The Hope 特會 App 登入連結"
LOGIN_VERIFICATION_EMAIL_TEMPLATE_NAME = "login_verification_email.html"


class LoginVerificationEmailProvider:
    """Send login verification email with custom template."""

    def __init__(self, template_render_provider, smtp_client: SmtpClient):
        self._template_render_provider = template_render_provider
        self._smtp_client = smtp_client

    @distributed_trace()
    async def send_login_verification_email(
        self,
        to_email: str,
        sign_in_link: str,
        member_name: str,
    ) -> None:
        """
        Render the login verification template and send via SMTP.
        :param to_email: Recipient email address.
        :param sign_in_link: Firebase sign-in link URL to embed in the email.
        :param member_name: Display name for greeting (e.g. first name or email).
        """
        html_body = await self._template_render_provider.render_email_by_file(
            name=LOGIN_VERIFICATION_EMAIL_TEMPLATE_NAME,
            sign_in_link=sign_in_link,
            member_name=member_name,
        )
        session = self._smtp_client.create()
        session.add_to(to_email).subject(LOGIN_VERIFICATION_EMAIL_SUBJECT).html(html_body)
        await session.asend()

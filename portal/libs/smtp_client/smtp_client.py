"""SMTP client"""
import asyncio
import logging
import mimetypes
import smtplib
import ssl
import sys
import time
from dataclasses import dataclass
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import aiosmtplib
from portal.config import settings

request_logger = logging.getLogger("smtp_client")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter(
        fmt="[%(asctime)s] %(name)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    )
)
request_logger.addHandler(handler)
request_logger.setLevel(logging.DEBUG)


@dataclass
class SmtpDefaults:
    """SmtpDefaults"""
    host: str = None
    port: int = 587
    username: str = None
    password: str = None
    from_email: str = None
    use_tls: bool = True
    use_ssl: Optional[bool] = None
    timeout: int = 30
    retry_interval: int = 5
    verbose: bool = None


@dataclass
class SmtpOptions:
    """SmtpOptions"""
    # pylint: disable=too-many-instance-attributes
    to: Optional[Union[str, List[str]]] = None
    cc: Optional[Union[str, List[str]]] = None
    bcc: Optional[Union[str, List[str]]] = None
    subject: str = None
    text: Optional[str] = None
    html: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None
    attachments: Optional[List[Union[str, Path]]] = None
    verbose: Optional[bool] = None
    timeout: Optional[int] = None
    max_retries: Optional[int] = None
    retry_interval: Optional[int] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None


class SmtpResponse:
    """SmtpResponse"""

    def __init__(self, message_id: Optional[str] = None, recipients: Optional[List[str]] = None):
        self.message_id = message_id
        self.recipients = recipients or []
        self.success = message_id is not None

    def __bool__(self):
        return self.success

    def __repr__(self):
        return f"SmtpResponse(success={self.success}, recipients={len(self.recipients)})"


class SmtpSession:
    """SmtpSession"""

    def __init__(
        self,
        defaults: SmtpDefaults = None,
        options: SmtpOptions = None
    ):
        self._options = options or SmtpOptions()
        self.defaults: SmtpDefaults = defaults
        self._st = time.time()

    @property
    def options(self):
        """options"""
        return self._options

    def verbose(self, verbose: bool):
        """verbose"""
        self._options.verbose = verbose
        return self

    def retry(self, max_retries: int, retry_interval: int = 5):
        """retry"""
        self._options.max_retries = max_retries
        self._options.retry_interval = retry_interval
        return self

    def timeout(self, timeout: int):
        """timeout"""
        self._options.timeout = timeout
        return self

    def add_to(self, recipients: Union[str, list[str]]):
        """add_to"""
        if not recipients:
            return self
        if not self._options.to:
            self._options.to = []
        if isinstance(recipients, str):
            recipients = [recipients]
        self._options.to.extend(recipients)
        self._options.to = list(set(self._options.to))
        return self

    def add_cc(self, recipients: Union[str, list[str]]):
        """add_cc"""
        if not recipients:
            return self
        if not self._options.cc:
            self._options.cc = []
        if isinstance(recipients, str):
            recipients = [recipients]
        self._options.cc.extend(recipients)
        self._options.cc = list(set(self._options.cc))
        return self

    def add_bcc(self, recipients: Union[str, list[str]]):
        """add_bcc"""
        if not recipients:
            return self
        if not self._options.bcc:
            self._options.bcc = []
        if isinstance(recipients, str):
            recipients = [recipients]
        self._options.bcc.extend(recipients)
        self._options.bcc = list(set(self._options.bcc))
        return self

    def subject(self, subject: str):
        """subject"""
        self._options.subject = subject
        return self

    def text(self, text: str):
        """text"""
        self._options.text = text
        return self

    def html(self, html: str):
        """html"""
        self._options.html = html
        return self

    def from_email(self, from_email: str):
        """from_email"""
        self._options.from_email = from_email
        return self

    def reply_to(self, reply_to: str):
        """reply_to"""
        self._options.reply_to = reply_to
        return self

    def attach(self, file_path: Union[str, Path]):
        """attach"""
        if not file_path:
            return self
        if not self._options.attachments:
            self._options.attachments = []
        path = Path(file_path) if isinstance(file_path, str) else file_path
        if path not in self._options.attachments:
            self._options.attachments.append(path)
        return self

    def attach_multiple(self, file_paths: Iterable[Union[str, Path]]):
        """attach_multiple"""
        if not file_paths:
            return self
        for file_path in file_paths:
            self.attach(file_path)
        return self

    def use_tls(self, use_tls: bool):
        """use_tls"""
        self._options.use_tls = use_tls
        return self

    def use_ssl(self, use_ssl: bool):
        """use_ssl"""
        self._options.use_ssl = use_ssl
        return self

    def _log_verbose(self, message: Any, *args):
        if self._options.verbose is False:
            return
        if self.defaults.verbose is not True:
            return
        if isinstance(message, str):
            request_logger.info(message, *args)
        elif callable(message):
            request_logger.info(message(), *args)

    def _normalize_recipients(self, recipients: Optional[Union[str, List[str]]]) -> List[str]:
        if not recipients:
            return []
        if isinstance(recipients, str):
            return [recipients]
        return list(recipients)

    def _build_message(self) -> MIMEMultipart:
        to_list = self._normalize_recipients(self._options.to)
        cc_list = self._normalize_recipients(self._options.cc)
        bcc_list = self._normalize_recipients(self._options.bcc)

        if not to_list and not cc_list and not bcc_list:
            raise ValueError("At least one recipient (to, cc, or bcc) must be specified")

        if not self._options.subject:
            raise ValueError("Subject must be specified")

        if not self._options.text and not self._options.html:
            raise ValueError("Either text or html content must be provided")

        from_email = self._options.from_email or self.defaults.from_email
        if not from_email:
            raise ValueError("From email must be specified")

        has_attachments = bool(self._options.attachments)
        has_both_text_html = bool(self._options.text and self._options.html)

        if has_both_text_html:
            msg = MIMEMultipart("alternative")
        else:
            msg = MIMEMultipart()

        msg["From"] = from_email
        if to_list:
            msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = self._options.subject

        if self._options.reply_to:
            msg["Reply-To"] = self._options.reply_to

        # Content handling
        if has_both_text_html:
            # Both text and HTML: create alternative part
            if has_attachments:
                # Need nested structure: mixed -> alternative
                content_part = MIMEMultipart("alternative")
                text_part = MIMEText(self._options.text, "plain", "utf-8")
                html_part = MIMEText(self._options.html, "html", "utf-8")
                content_part.attach(text_part)
                content_part.attach(html_part)
                msg.attach(content_part)
            else:
                # No attachments, use alternative directly
                text_part = MIMEText(self._options.text, "plain", "utf-8")
                html_part = MIMEText(self._options.html, "html", "utf-8")
                msg.attach(text_part)
                msg.attach(html_part)
        elif self._options.html:
            # HTML only: add fallback text
            if has_attachments:
                content_part = MIMEMultipart("alternative")
                html_part = MIMEText(self._options.html, "html", "utf-8")
                content_part.attach(html_part)
                msg.attach(content_part)
            else:
                html_part = MIMEText(self._options.html, "html", "utf-8")
                msg.attach(html_part)
        else:
            # Text only
            text_part = MIMEText(self._options.text or "", "plain", "utf-8")
            msg.attach(text_part)

        # Attachments
        if self._options.attachments:
            for path in self._options.attachments:
                path_obj = Path(path) if isinstance(path, str) else path
                if not path_obj.exists() or not path_obj.is_file():
                    request_logger.warning(f"SMTP attachment not found: {path_obj}")
                    continue
                ctype, encoding = mimetypes.guess_type(str(path_obj))
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)

                with path_obj.open("rb") as f:
                    attachment = MIMEBase(maintype, subtype)
                    attachment.set_payload(f.read())

                # Encode the attachment
                from email import encoders
                encoders.encode_base64(attachment)

                # Add header
                attachment.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{path_obj.name}"'
                )
                msg.attach(attachment)

        return msg

    def _get_smtp_config(self) -> Dict[str, Any]:
        return {
            "host": self.defaults.host,
            "port": self.defaults.port,
            "timeout": self._options.timeout or self.defaults.timeout,
        }

    def _decide_ssl_mode(self) -> str:
        use_ssl = self._options.use_ssl
        if use_ssl is not None:
            return "ssl" if use_ssl else "starttls"

        use_ssl_default = self.defaults.use_ssl
        if use_ssl_default is not None:
            return "ssl" if use_ssl_default else "starttls"

        port = self.defaults.port
        if port == 465:
            return "ssl"
        if port in (587, 25):
            use_tls = self._options.use_tls
            if use_tls is not None:
                return "starttls" if use_tls else "plain"
            if self.defaults.use_tls:
                return "starttls"
        return "plain"

    def _send_message(
        self,
        message: MIMEMultipart,
        recipients: List[str]
    ) -> SmtpResponse:
        config = self._get_smtp_config()
        ssl_mode = self._decide_ssl_mode()

        try:
            if ssl_mode == "ssl":
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    config["host"],
                    config["port"],
                    timeout=config["timeout"],
                    context=context
                ) as server:
                    self._login_if_needed(server)
                    server.send_message(
                        message,
                        from_addr=self._options.from_email or self.defaults.from_email,
                        to_addrs=recipients
                    )
            else:
                with smtplib.SMTP(
                    config["host"],
                    config["port"],
                    timeout=config["timeout"]
                ) as server:
                    server.ehlo()
                    if ssl_mode == "starttls":
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                        server.ehlo()
                    self._login_if_needed(server)
                    server.send_message(
                        message,
                        from_addr=self._options.from_email or self.defaults.from_email,
                        to_addrs=recipients
                    )

            message_id = message.get("Message-ID", "")
            return SmtpResponse(message_id=message_id, recipients=recipients)
        except Exception as exc:
            request_logger.error(f"SMTP send failed: {exc}")
            raise

    def _login_if_needed(self, server: smtplib.SMTP):
        username = self.defaults.username
        password = self.defaults.password
        if username and password:
            server.login(username, password)
        else:
            self._log_verbose("SMTP login skipped (no username/password provided)")

    async def _alogin_if_needed(self, server: aiosmtplib.SMTP):
        username = self.defaults.username
        password = self.defaults.password
        if username and password:
            await server.login(username, password)
        else:
            self._log_verbose("SMTP login skipped (no username/password provided)")

    async def _asend_message(
        self,
        message: MIMEMultipart,
        recipients: List[str]
    ) -> SmtpResponse:
        config = self._get_smtp_config()
        ssl_mode = self._decide_ssl_mode()
        sender = self._options.from_email or self.defaults.from_email

        try:
            if ssl_mode == "ssl":
                # SSL mode: use direct TLS connection (port 465)
                context = ssl.create_default_context()
                async with aiosmtplib.SMTP(
                    hostname=config["host"],
                    port=config["port"],
                    timeout=config["timeout"],
                    use_tls=True,
                    tls_context=context
                ) as server:
                    await self._alogin_if_needed(server)
                    await server.send_message(
                        message,
                        sender=sender,
                        recipients=recipients
                    )
            elif ssl_mode == "starttls":
                # STARTTLS mode: connect without TLS, then upgrade (port 587/25)
                context = ssl.create_default_context()
                async with aiosmtplib.SMTP(
                    hostname=config["host"],
                    port=config["port"],
                    timeout=config["timeout"],
                    use_tls=False,
                    tls_context=context
                ) as server:
                    await self._alogin_if_needed(server)
                    await server.send_message(
                        message,
                        sender=sender,
                        recipients=recipients
                    )
            else:
                # Plain mode: no encryption
                async with aiosmtplib.SMTP(
                    hostname=config["host"],
                    port=config["port"],
                    timeout=config["timeout"],
                    use_tls=False
                ) as server:
                    await self._alogin_if_needed(server)
                    await server.send_message(
                        message,
                        sender=sender,
                        recipients=recipients
                    )

            message_id = message.get("Message-ID", "")
            return SmtpResponse(message_id=message_id, recipients=recipients)
        except Exception as exc:
            request_logger.error(f"SMTP send failed: {exc}")
            raise

    def _format_log_message(self, recipients: List[str]) -> str:
        esp = time.time() - self._st
        return f"Email sent to {len(recipients)} recipients ({round(esp * 1000)}ms)"

    def _format_response(
        self,
        response: SmtpResponse,
        retry_count: int,
        is_last_time: bool
    ):
        if not response.success:
            if not is_last_time:
                request_logger.debug(
                    f'SMTP send failed, ready to retry {retry_count + 1} times'
                )
                return None
            request_logger.debug('SMTP send failed after all retries')
        self._log_verbose(lambda: self._format_log_message(response.recipients))
        return response

    def _retry_error_debug_log(
        self,
        is_last_time: bool,
        exception: Exception,
        retry_count: int
    ):
        if not is_last_time:
            request_logger.debug(
                f'SMTP send error: {str(exception)} '
                f'Ready to retry {retry_count + 1} times'
            )
        else:
            request_logger.debug(
                f'SMTP send error: {str(exception)} '
                f'Maximum number of retries reached'
            )

    def send(self) -> SmtpResponse:
        """send"""
        message = self._build_message()
        to_list = self._normalize_recipients(self._options.to)
        cc_list = self._normalize_recipients(self._options.cc)
        bcc_list = self._normalize_recipients(self._options.bcc)
        recipients = to_list + cc_list + bcc_list

        self._log_verbose(
            lambda: f'Sending email to {len(recipients)} recipients: {", ".join(recipients)}'
        )
        self._log_verbose(lambda: f'Subject: {self._options.subject}')

        max_retries = 1 if not self._options.max_retries else self._options.max_retries + 1
        for i in range(max_retries):
            is_last_time = (i + 1) == max_retries
            try:
                response = self._send_message(message, recipients)
                if not response.success and not is_last_time:
                    if self._options.retry_interval is not None:
                        time.sleep(self._options.retry_interval)
                    continue
                formatted_response = self._format_response(
                    response,
                    retry_count=i,
                    is_last_time=is_last_time
                )
                if not formatted_response:
                    continue
                return formatted_response
            except (
                smtplib.SMTPException,
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPConnectError,
                smtplib.SMTPAuthenticationError,
                ConnectionRefusedError,
                TimeoutError,
                OSError
            ) as exc:
                if is_last_time:
                    raise exc
                if self._options.retry_interval is not None:
                    time.sleep(self._options.retry_interval)
                self._retry_error_debug_log(
                    is_last_time=is_last_time,
                    exception=exc,
                    retry_count=i
                )
                continue

    async def asend(self) -> SmtpResponse:
        """asend"""
        message = self._build_message()
        to_list = self._normalize_recipients(self._options.to)
        cc_list = self._normalize_recipients(self._options.cc)
        bcc_list = self._normalize_recipients(self._options.bcc)
        recipients = to_list + cc_list + bcc_list

        self._log_verbose(
            lambda: f'Sending email to {len(recipients)} recipients: {", ".join(recipients)}'
        )
        self._log_verbose(lambda: f'Subject: {self._options.subject}')

        max_retries = 1 if not self._options.max_retries else self._options.max_retries + 1
        for i in range(max_retries):
            is_last_time = (i + 1) == max_retries
            try:
                response = await self._asend_message(message, recipients)
                if not response.success and not is_last_time:
                    if self._options.retry_interval is not None:
                        await asyncio.sleep(self._options.retry_interval)
                    continue
                formatted_response = self._format_response(
                    response,
                    retry_count=i,
                    is_last_time=is_last_time
                )
                if not formatted_response:
                    continue
                return formatted_response
            except (
                ConnectionRefusedError,
                TimeoutError,
                OSError,
                aiosmtplib.SMTPException,
                aiosmtplib.SMTPServerDisconnected,
                aiosmtplib.SMTPConnectError,
                aiosmtplib.SMTPAuthenticationError
            ) as exc:
                if is_last_time:
                    raise exc
                if self._options.retry_interval is not None:
                    await asyncio.sleep(self._options.retry_interval)
                self._retry_error_debug_log(
                    is_last_time=is_last_time,
                    exception=exc,
                    retry_count=i
                )
                continue


# pylint: disable=too-few-public-methods
class SmtpClient:
    """SmtpClient"""

    def __init__(self, defaults: SmtpDefaults = None):
        if defaults is None:
            defaults = SmtpDefaults(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                from_email=settings.SMTP_FROM_EMAIL,
                use_tls=True,
                verbose=settings.is_dev
            )
        self.defaults: SmtpDefaults = defaults

    def create(self) -> SmtpSession:
        """
        :return:
        """
        return SmtpSession(self.defaults, SmtpOptions())


smtp_client = SmtpClient()


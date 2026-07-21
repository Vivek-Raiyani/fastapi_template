"""Email sending — console or SMTP."""

import logging
from email.message import EmailMessage

import aiosmtplib

from core.settings import settings
from core.templating import templates

logger = logging.getLogger(__name__)


async def send_email(
    *, to: str, subject: str, html_body: str, text_body: str | None = None
) -> None:
    if settings.EMAIL_BACKEND == "console":
        logger.info("--- EMAIL to=%s subject=%s ---\n%s", to, subject, html_body)
        return

    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body or html_body)
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER or None,
        password=settings.SMTP_PASSWORD or None,
        start_tls=settings.SMTP_TLS,
    )


async def send_template_email(*, to: str, subject: str, template: str, context: dict) -> None:
    html = templates.env.get_template(template).render(**context, settings=settings)
    await send_email(to=to, subject=subject, html_body=html)

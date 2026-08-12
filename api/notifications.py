"""
Outbound delivery for public form submissions.

Every submission is FIRST stored in PostgreSQL, then delivered to:

- Google Form
- WhatsApp link
- Email notification

IMPORTANT:
External services must NEVER cause the API request to fail.
"""

from __future__ import annotations

import logging
import re
import threading

from urllib.parse import quote, urlencode

import requests

from django.conf import settings
from django.core.mail import EmailMessage

log = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

GOOGLE_FORM_TIMEOUT = 10


# ============================================================
# BACKGROUND TASK
# ============================================================

def run_in_background(fn, *args, **kwargs):
    """
    Run external delivery jobs outside the API request.

    Contact/enquiry data is already saved to PostgreSQL before
    this function is called.

    SMTP, Google Forms or other external failures must never
    cause the API endpoint to return HTTP 500.
    """

    delivery_async = getattr(
        settings,
        "DELIVERY_ASYNC",
        True,
    )

    # --------------------------------------------------------
    # Synchronous mode
    # Useful only for debugging/tests.
    # --------------------------------------------------------

    if not delivery_async:
        try:
            return fn(*args, **kwargs)

        except BaseException:
            log.exception(
                "Inline delivery job failed: %s",
                getattr(fn, "__name__", str(fn)),
            )

            return None

    # --------------------------------------------------------
    # Background mode
    # --------------------------------------------------------

    def _runner():
        try:
            fn(*args, **kwargs)

        except BaseException:
            log.exception(
                "Background delivery job failed: %s",
                getattr(fn, "__name__", str(fn)),
            )

    try:
        thread = threading.Thread(
            target=_runner,
            name=f"delivery-{getattr(fn, '__name__', 'job')}",
            daemon=True,
        )

        thread.start()

        log.info(
            "Background delivery started: %s",
            getattr(fn, "__name__", str(fn)),
        )

    except Exception:
        log.exception(
            "Could not start background delivery: %s",
            getattr(fn, "__name__", str(fn)),
        )

    return None


# ============================================================
# GOOGLE FORM
# ============================================================

def _google_form_url(form_id_or_url: str) -> str:
    """
    Accept:

    - Google Form ID
    - Google Form view URL
    - Prefilled URL
    - formResponse URL

    Returns:
        https://docs.google.com/forms/d/e/FORM_ID/formResponse
    """

    value = (form_id_or_url or "").strip()

    match = re.search(
        r"/forms/d/e/([^/?#]+)",
        value,
    )

    form_id = (
        match.group(1)
        if match
        else value.strip("/")
    )

    if not form_id or not re.fullmatch(
        r"[A-Za-z0-9_-]+",
        form_id,
    ):
        raise ValueError(
            "GOOGLE_FORM_ID must be a form ID or Google Forms URL."
        )

    return (
        f"https://docs.google.com/forms/d/e/"
        f"{form_id}/formResponse"
    )


def post_to_google_form(
    values: dict[str, str],
    form_id: str | None = None,
) -> dict:
    """
    Submit values to Google Forms.

    Example:

    values = {
        "name": "John",
        "email": "john@example.com",
        "phone": "123456789",
        "message": "Hello"
    }

    Field IDs come from:

        settings.GOOGLE_FORM_ENTRIES
    """

    try:
        form_id = (
            form_id
            or getattr(settings, "GOOGLE_FORM_ID", "")
        )

        entries = getattr(
            settings,
            "GOOGLE_FORM_ENTRIES",
            {},
        )

        if not form_id:
            return {
                "ok": False,
                "skipped": True,
                "reason": "GOOGLE_FORM_ID not configured",
            }

        payload = {}

        for key, value in values.items():

            entry_id = (
                entries.get(key)
                or ""
            ).strip()

            # Allow both:
            # 123456789
            # entry.123456789

            if (
                entry_id
                and not entry_id.startswith("entry.")
            ):
                entry_id = f"entry.{entry_id}"

            if (
                entry_id
                and value not in (None, "")
            ):
                payload[entry_id] = str(value)[:2000]

        if not payload:
            return {
                "ok": False,
                "skipped": True,
                "reason": (
                    "No mapped GOOGLE_FORM_ENTRY fields"
                ),
            }

        url = _google_form_url(form_id)

        submit_payload = {
            "fvv": "1",
            "pageHistory": "0",
            **payload,
        }

        response = requests.post(
            url,
            data=submit_payload,
            timeout=GOOGLE_FORM_TIMEOUT,
            allow_redirects=False,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; CircuitTravelAPI/1.0)"
                ),
                "Referer": url.replace(
                    "/formResponse",
                    "/viewform",
                ),
            },
        )

        ok = response.status_code in (
            200,
            302,
        )

        result = {
            "ok": ok,
            "status": response.status_code,
            "submitted_fields": sorted(
                payload.keys()
            ),
        }

        if not ok:
            result["error"] = (
                f"Google Forms returned "
                f"HTTP {response.status_code}"
            )

        log.info(
            "Google Form delivery result: %s",
            result,
        )

        return result

    except Exception as exc:

        log.exception(
            "Google Form delivery failed"
        )

        return {
            "ok": False,
            "error": str(exc),
        }


# ============================================================
# WHATSAPP
# ============================================================

def build_whatsapp_link(
    text: str,
    number: str | None = None,
) -> str:
    """
    Build a WhatsApp wa.me URL.

    Example:

    https://wa.me/971501234567?text=Hello
    """

    whatsapp_number = getattr(
        settings,
        "WHATSAPP_NUMBER",
        "",
    )

    number = re.sub(
        r"\D",
        "",
        str(
            number
            or whatsapp_number
            or ""
        ),
    )

    if not 8 <= len(number) <= 15:

        log.error(
            "WHATSAPP_NUMBER is missing or invalid"
        )

        return ""

    return (
        f"https://wa.me/{number}?"
        f"{urlencode({'text': text}, quote_via=quote)}"
    )


# ============================================================
# EMAIL
# ============================================================

def send_notification_email(
    subject: str,
    body: str,
    reply_to: str = "",
) -> dict:
    """
    Send an email notification.

    Email errors are always caught and returned as a dictionary.
    They never raise an exception to the contact API.
    """

    try:

        recipients = getattr(
            settings,
            "CONTACT_NOTIFY_EMAILS",
            [],
        )

        to = [
            addr
            for addr in recipients
            if addr
        ]

        if not to:

            return {
                "ok": False,
                "skipped": True,
                "reason": (
                    "CONTACT_NOTIFY_EMAILS "
                    "not configured"
                ),
            }

        message = EmailMessage(
            subject=subject[:180],
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
            reply_to=(
                [reply_to]
                if reply_to
                else None
            ),
        )

        message.send(
            fail_silently=False
        )

        log.info(
            "Notification email sent to: %s",
            to,
        )

        return {
            "ok": True,
            "to": to,
        }

    except BaseException as exc:

        log.exception(
            "Email delivery failed"
        )

        return {
            "ok": False,
            "error": str(exc),
        }


# ============================================================
# ENQUIRY HELPERS
# ============================================================

def _enquiry_text(enquiry) -> str:

    lines = [
        (
            f"{settings.SITE_NAME} — "
            f"{'Visa Enquiry' if enquiry.is_visa else 'Enquiry'}"
        ),

        (
            f"{(enquiry.item_type or 'Item').title()}: "
            f"{enquiry.item_title}"
            if enquiry.item_title
            else ""
        ),

        f"Name: {enquiry.name}",

        f"Email: {enquiry.email or '-'}",

        f"Phone: {enquiry.phone or '-'}",
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    if enquiry.message:

        lines.append(
            f"Message: {enquiry.message}"
        )

    return "\n".join(lines)


def _to_whatsapp(enquiry) -> bool:
    """
    Visa enquiries and assistance callback requests
    go to WhatsApp.
    """

    return bool(
        enquiry.is_visa
        or getattr(
            enquiry,
            "channel",
            "",
        ) == "whatsapp"
        or (
            getattr(
                enquiry,
                "source",
                "",
            )
            or ""
        ) == "assistance"
    )


# ============================================================
# PREPARE ENQUIRY
# ============================================================

def prepare_enquiry(enquiry) -> str:
    """
    Prepare WhatsApp link.

    This contains no external network request.
    """

    if not _to_whatsapp(enquiry):

        return ""

    link = build_whatsapp_link(
        _enquiry_text(enquiry)
    )

    try:

        if link != enquiry.whatsapp_url:

            enquiry.whatsapp_url = link

            enquiry.save(
                update_fields=[
                    "whatsapp_url",
                    "updated_at",
                ]
            )

    except Exception:

        log.exception(
            "Could not save WhatsApp URL"
        )

    return link


# ============================================================
# DELIVER ENQUIRY
# ============================================================

def deliver_enquiry(enquiry) -> dict:
    """
    Deliver an already saved enquiry.

    Possible destinations:

    - WhatsApp
    - Google Form
    - Email

    Failure of one destination does not stop the others.
    """

    report = {}

    # --------------------------------------------------------
    # WhatsApp
    # --------------------------------------------------------

    if _to_whatsapp(enquiry):

        try:

            link = (
                enquiry.whatsapp_url
                or build_whatsapp_link(
                    _enquiry_text(enquiry)
                )
            )

            if link:

                enquiry.whatsapp_url = link

            report["whatsapp"] = {
                "ok": bool(link),
                "url": link,
            }

        except Exception as exc:

            log.exception(
                "WhatsApp link generation failed"
            )

            report["whatsapp"] = {
                "ok": False,
                "error": str(exc),
            }

    # --------------------------------------------------------
    # Google Form
    # --------------------------------------------------------

    else:

        try:

            result = post_to_google_form({
                "name": enquiry.name,
                "email": enquiry.email,
                "phone": enquiry.phone,
                "message": enquiry.message,
                "type": "enquiry",
                "item_title": enquiry.item_title,
                "item_type": enquiry.item_type,
            })

            enquiry.google_form_sent = bool(
                result.get("ok")
            )

            report["google_form"] = result

        except Exception as exc:

            log.exception(
                "Enquiry Google Form failed"
            )

            report["google_form"] = {
                "ok": False,
                "error": str(exc),
            }

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    if getattr(
        settings,
        "NOTIFY_ENQUIRY_BY_EMAIL",
        False,
    ):

        try:

            mail = send_notification_email(
                subject=(
                    f"[{settings.SITE_NAME}] "
                    f"New enquiry — "
                    f"{enquiry.item_title or enquiry.name}"
                ),
                body=_enquiry_text(enquiry),
                reply_to=enquiry.email,
            )

            enquiry.email_sent = bool(
                mail.get("ok")
            )

            report["email"] = mail

        except Exception as exc:

            log.exception(
                "Enquiry email failed"
            )

            report["email"] = {
                "ok": False,
                "error": str(exc),
            }

    # --------------------------------------------------------
    # Save delivery status
    # --------------------------------------------------------

    try:

        enquiry.delivery_log = report

        enquiry.save(
            update_fields=[
                "whatsapp_url",
                "google_form_sent",
                "email_sent",
                "delivery_log",
                "updated_at",
            ]
        )

    except Exception:

        log.exception(
            "Could not save enquiry delivery status"
        )

    return report


# ============================================================
# DELIVER CONTACT MESSAGE
# ============================================================

def deliver_contact_message(msg) -> dict:
    """
    Contact page delivery.

    The contact message is already saved in PostgreSQL.

    Then:
    1. Send email notification
    2. Submit to Google Form

    Neither failure can crash the API.
    """

    body = "\n".join([
        f"{settings.SITE_NAME} — Contact message",

        f"Service: {msg.service or '-'}",

        f"Name: {msg.name}",

        f"Email: {msg.email or '-'}",

        f"Phone: {msg.phone or '-'}",

        "",

        "Message:",

        msg.message or "",
    ])

    # Default delivery results

    mail = {
        "ok": False,
        "skipped": True,
        "reason": "Email not attempted",
    }

    form = {
        "ok": False,
        "skipped": True,
        "reason": "Google Form not attempted",
    }

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    try:

        mail = send_notification_email(
            subject=(
                f"[{settings.SITE_NAME}] "
                f"Contact — "
                f"{msg.service or msg.name}"
            ),
            body=body,
            reply_to=msg.email,
        )

    except BaseException as exc:

        log.exception(
            "Contact email delivery failed "
            "for contact %s",
            msg.pk,
        )

        mail = {
            "ok": False,
            "error": str(exc),
        }

    # --------------------------------------------------------
    # GOOGLE FORM
    # --------------------------------------------------------

    try:

        form = post_to_google_form({
            "name": msg.name,
            "email": msg.email,
            "phone": msg.phone,
            "item_title": msg.service,
            "message": msg.message,
            "type": "contact",
        })

    except BaseException as exc:

        log.exception(
            "Contact Google Form delivery failed "
            "for contact %s",
            msg.pk,
        )

        form = {
            "ok": False,
            "error": str(exc),
        }

    # --------------------------------------------------------
    # UPDATE DATABASE
    # --------------------------------------------------------

    report = {
        "email": mail,
        "google_form": form,
    }

    try:

        msg.email_sent = bool(
            mail.get("ok")
        )

        msg.google_form_sent = bool(
            form.get("ok")
        )

        msg.delivery_log = report

        msg.save(
            update_fields=[
                "email_sent",
                "google_form_sent",
                "delivery_log",
                "updated_at",
            ]
        )

    except Exception:

        log.exception(
            "Could not update contact delivery status "
            "for contact %s",
            msg.pk,
        )

    return report
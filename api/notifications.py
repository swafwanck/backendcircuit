"""
Outbound delivery for public form submissions.

Every submission is FIRST stored in PostgreSQL, then fanned out to:

  * Google Form  -> server-side POST to /formResponse (no client secrets leaked)
  * WhatsApp     -> wa.me deep link built server-side (NO third-party provider)
  * Email (Gmail)-> Django SMTP (Gmail app password) to CONTACT_NOTIFY_EMAIL

Routing rules (as configured by the project):
  - Visa enquiries          -> WhatsApp (+ DB), NOT Google Form
  - All other enquiries     -> Google Form (+ DB)
  - Contact page messages    -> Gmail + Google Form (+ DB)

Delivery never raises: a transport failure must not lose the database row.
"""
from __future__ import annotations

import logging
import re
import threading
from urllib.parse import quote, urlencode, urlparse

import requests
from django.conf import settings
from django.core.mail import EmailMessage

log = logging.getLogger(__name__)

TIMEOUT = 8  # seconds — keep request/response fast


def run_in_background(fn, *args, **kwargs):
    """
    Run a delivery job off the request thread so the visitor never waits for
    Google Form / SMTP round-trips (and never sees a 500 when they fail).
    Set DELIVERY_ASYNC=False to run inline (tests / debugging).
    """
    if not getattr(settings, "DELIVERY_ASYNC", True):
        try:
            return fn(*args, **kwargs)
        except Exception:
            log.exception("Delivery job failed: %s", getattr(fn, "__name__", fn))
            return None

    def _runner():
        try:
            fn(*args, **kwargs)
        except Exception:
            log.exception("Delivery job failed: %s", getattr(fn, "__name__", fn))

    threading.Thread(target=_runner, daemon=True).start()
    return None


# --------------------------------------------------------------------------- #
# Google Form
# --------------------------------------------------------------------------- #
def _google_form_url(form_id_or_url: str) -> str:
    """Accept a Google Form ID, view URL, prefilled URL, or response URL."""
    value = (form_id_or_url or "").strip()
    match = re.search(r"/forms/d/e/([^/?#]+)", value)
    form_id = match.group(1) if match else value.strip("/")
    if not form_id or not re.fullmatch(r"[A-Za-z0-9_-]+", form_id):
        raise ValueError(
            "GOOGLE_FORM_ID must be a form ID or a Google Forms /viewform URL."
        )
    return f"https://docs.google.com/forms/d/e/{form_id}/formResponse"


def post_to_google_form(values: dict[str, str], form_id: str | None = None) -> dict:
    """
    values: {"name": "...", "email": "...", ...} — logical keys.
    Mapped to `entry.XXXX` ids from settings.GOOGLE_FORM_ENTRIES.
    """
    form_id = form_id or settings.GOOGLE_FORM_ID
    entries = settings.GOOGLE_FORM_ENTRIES
    if not form_id:
        return {"ok": False, "skipped": True, "reason": "GOOGLE_FORM_ID not configured"}

    payload = {}
    for key, value in values.items():
        entry_id = (entries.get(key) or "").strip()
        if entry_id and not entry_id.startswith("entry."):
            entry_id = f"entry.{entry_id}"
        if entry_id and value not in (None, ""):
            payload[entry_id] = str(value)[:2000]
    if not payload:
        return {"ok": False, "skipped": True, "reason": "no mapped GOOGLE_FORM_ENTRY_* fields"}

    try:
        url = _google_form_url(form_id)
        # Google Forms expects these browser fields in addition to entry.* values.
        submit_payload = {"fvv": "1", "pageHistory": "0", **payload}
        resp = requests.post(
            url,
            data=submit_payload,
            timeout=TIMEOUT,
            allow_redirects=False,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CircuitTravelAPI/1.0)",
                "Referer": url.replace("/formResponse", "/viewform"),
            },
        )
        ok = resp.status_code in (200, 302)
        result = {"ok": ok, "status": resp.status_code, "submitted_fields": sorted(payload)}
        if not ok:
            result["error"] = f"Google Forms returned HTTP {resp.status_code}"
        log.info("Google Form delivery result: %s", result)
        return result
    except (ValueError, requests.RequestException) as exc:  # pragma: no cover - network
        log.warning("Google Form delivery failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# --------------------------------------------------------------------------- #
# WhatsApp (no third-party API/provider — plain wa.me deep link)
# --------------------------------------------------------------------------- #
def build_whatsapp_link(text: str, number: str | None = None) -> str:
    # wa.me accepts an international number containing digits only. Tolerate
    # common .env formats such as "+971 50 247 5643" while rejecting malformed
    # values instead of producing a broken URL.
    number = re.sub(r"\D", "", str(number or settings.WHATSAPP_NUMBER or ""))
    if not 8 <= len(number) <= 15:
        log.error("WHATSAPP_NUMBER is missing or invalid; use 8-15 digits including country code")
        return ""
    return f"https://wa.me/{number}?{urlencode({'text': text}, quote_via=quote)}"


# --------------------------------------------------------------------------- #
# Email (Gmail SMTP)
# --------------------------------------------------------------------------- #
def send_notification_email(subject: str, body: str, reply_to: str = "") -> dict:
    to = [addr for addr in settings.CONTACT_NOTIFY_EMAILS if addr]
    if not to:
        return {"ok": False, "skipped": True, "reason": "CONTACT_NOTIFY_EMAILS not configured"}
    try:
        msg = EmailMessage(
            subject=subject[:180],
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
            reply_to=[reply_to] if reply_to else None,
        )
        msg.send(fail_silently=False)
        return {"ok": True, "to": to}
    except Exception as exc:  # pragma: no cover - SMTP
        log.warning("Email delivery failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# --------------------------------------------------------------------------- #
# High-level delivery
# --------------------------------------------------------------------------- #
def _enquiry_text(enquiry) -> str:
    lines = [
        f"{settings.SITE_NAME} — {'Visa Enquiry' if enquiry.is_visa else 'Enquiry'}",
        f"{(enquiry.item_type or 'Item').title()}: {enquiry.item_title}" if enquiry.item_title else "",
        f"Name: {enquiry.name}",
        f"Email: {enquiry.email or '-'}",
        f"Phone: {enquiry.phone or '-'}",
    ]
    lines = [ln for ln in lines if ln]
    if enquiry.message:
        lines.append(f"Message: {enquiry.message}")
    return "\n".join(lines)


def _to_whatsapp(enquiry) -> bool:
    """Visa enquiries and call-back (assistance) requests go to WhatsApp."""
    return bool(
        enquiry.is_visa
        or getattr(enquiry, "channel", "") == "whatsapp"
        or (getattr(enquiry, "source", "") or "") == "assistance"
    )


def prepare_enquiry(enquiry) -> str:
    """
    Synchronous part of delivery: build the wa.me deep link for WhatsApp-routed
    enquiries so it can be returned in the API response. No network calls.
    """
    if not _to_whatsapp(enquiry):
        return ""
    link = build_whatsapp_link(_enquiry_text(enquiry))
    if link != enquiry.whatsapp_url:
        enquiry.whatsapp_url = link
        enquiry.save(update_fields=["whatsapp_url", "updated_at"])
    return link


def deliver_enquiry(enquiry) -> dict:
    """Fan out one stored Enquiry row. Returns a delivery report (also persisted)."""
    report: dict = {}

    if _to_whatsapp(enquiry):
        # Visa + call-back enquiries go to WhatsApp only (never Google Form).
        link = enquiry.whatsapp_url or build_whatsapp_link(_enquiry_text(enquiry))
        if link:
            enquiry.whatsapp_url = link
        report["whatsapp"] = {"ok": bool(link), "url": link}
    else:
        result = post_to_google_form({
            "name": enquiry.name,
            "email": enquiry.email,
            "phone": enquiry.phone,
            "message": enquiry.message,
            "type": "enquiry",
            "item_title": enquiry.item_title,
            "item_type": enquiry.item_type,
        })
        enquiry.google_form_sent = bool(result.get("ok"))
        report["google_form"] = result

    if settings.NOTIFY_ENQUIRY_BY_EMAIL:
        mail = send_notification_email(
            subject=f"[{settings.SITE_NAME}] New enquiry — {enquiry.item_title or enquiry.name}",
            body=_enquiry_text(enquiry),
            reply_to=enquiry.email,
        )
        enquiry.email_sent = bool(mail.get("ok"))
        report["email"] = mail

    enquiry.delivery_log = report
    enquiry.save(update_fields=[
        "whatsapp_url", "google_form_sent", "email_sent", "delivery_log", "updated_at",
    ])
    return report


def deliver_contact_message(msg) -> dict:
    """Contact page messages: Gmail + Google Form (+ already stored in DB)."""
    body = "\n".join([
        f"{settings.SITE_NAME} — Contact message",
        f"Service: {msg.service or '-'}",
        f"Name: {msg.name}",
        f"Email: {msg.email or '-'}",
        f"Phone: {msg.phone or '-'}",
        "",
        msg.message or "",
    ])

    mail = send_notification_email(
        subject=f"[{settings.SITE_NAME}] Contact — {msg.service or msg.name}",
        body=body,
        reply_to=msg.email,
    )
    form = post_to_google_form({
        "name": msg.name,
        "email": msg.email,
        "phone": msg.phone,
        "item_title": msg.service,
        "message": msg.message,
        "type": "contact",
    })

    msg.email_sent = bool(mail.get("ok"))
    msg.google_form_sent = bool(form.get("ok"))
    msg.delivery_log = {"email": mail, "google_form": form}
    msg.save(update_fields=[
        "email_sent", "google_form_sent", "delivery_log", "updated_at",
    ])
    return msg.delivery_log
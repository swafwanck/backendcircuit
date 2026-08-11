"""Adyen SDK wrapper — Sessions API + Pay By Link + webhook HMAC verification."""
import base64
import hmac
import hashlib
import binascii
from decimal import Decimal
from django.conf import settings

try:
    import Adyen  # type: ignore
except Exception:  # pragma: no cover
    Adyen = None


def _client():
    if Adyen is None:
        raise RuntimeError("Adyen SDK not installed. Run: pip install Adyen")
    a = Adyen.Adyen()
    a.payment.client.xapikey = settings.ADYEN_API_KEY
    a.payment.client.platform = settings.ADYEN_ENV  # "test" or "live"
    return a


def _minor_units(amount, currency: str) -> int:
    # Most currencies: 2 decimals. (JPY etc. differ, extend as needed.)
    d = Decimal(str(amount))
    return int((d * Decimal("100")).quantize(Decimal("1")))


def create_session(*, reference: str, amount, currency: str,
                   country_code: str = "AE", return_url: str = "", shopper_email: str = ""):
    """Adyen Checkout Sessions API — for Drop-in / Web Components."""
    a = _client()
    payload = {
        "amount": {"value": _minor_units(amount, currency), "currency": currency},
        "reference": reference,
        "merchantAccount": settings.ADYEN_MERCHANT_ACCOUNT,
        "returnUrl": return_url or f"{settings.FRONTEND_URL}/payment/return",
        "countryCode": country_code,
    }
    if shopper_email:
        payload["shopperEmail"] = shopper_email
    result = a.checkout.payments_api.sessions(payload)
    return result.message  # dict with id, sessionData, etc.


def create_pay_by_link(*, reference: str, amount, currency: str,
                       description: str = "", shopper_email: str = ""):
    """Adyen Pay By Link — returns a hosted payment URL."""
    a = _client()
    payload = {
        "amount": {"value": _minor_units(amount, currency), "currency": currency},
        "reference": reference,
        "merchantAccount": settings.ADYEN_MERCHANT_ACCOUNT,
        "description": description or reference,
        "returnUrl": f"{settings.FRONTEND_URL}/payment/return",
    }
    if shopper_email:
        payload["shopperEmail"] = shopper_email
    result = a.checkout.payment_links_api.payment_links(payload)
    return result.message  # dict with url, id, expiresAt


# ------- HMAC webhook verification (Adyen "standard notifications") -------
def _get_hmac_signature(item: dict) -> str:
    return (item.get("NotificationRequestItem", {})
                .get("additionalData", {})
                .get("hmacSignature", "")) or ""


def _sign_payload(item: dict) -> str:
    n = item["NotificationRequestItem"]
    amount = n.get("amount", {}) or {}
    fields = [
        n.get("pspReference", ""),
        n.get("originalReference", ""),
        n.get("merchantAccountCode", ""),
        n.get("merchantReference", ""),
        str(amount.get("value", "")),
        amount.get("currency", ""),
        n.get("eventCode", ""),
        n.get("success", ""),
    ]
    escaped = [str(f).replace("\\", "\\\\").replace(":", "\\:") for f in fields]
    signing_string = ":".join(escaped).encode("utf-8")
    key = binascii.a2b_hex(settings.ADYEN_HMAC_KEY)
    mac = hmac.new(key, signing_string, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("utf-8")


def verify_notification(item: dict) -> bool:
    if not settings.ADYEN_HMAC_KEY:
        return False
    expected = _sign_payload(item)
    received = _get_hmac_signature(item)
    return hmac.compare_digest(expected, received)

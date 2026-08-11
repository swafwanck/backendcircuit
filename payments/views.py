from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from api.models import Booking, Payment
from api.constants import PaymentStatus
from .serializers import (
    CreateSessionSerializer, CreatePayLinkSerializer, PublicPayLinkSerializer,
)
from . import adyen_client


@api_view(["POST"])
@permission_classes([AllowAny])
def create_session(request):
    """POST /api/payments/sessions/ — Drop-in Sessions."""
    s = CreateSessionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    booking = get_object_or_404(Booking, reference=d["booking_ref"])

    try:
        session = adyen_client.create_session(
            reference=booking.reference,
            amount=d["amount"], currency=d["currency"],
            country_code=d.get("country_code", "AE"),
            return_url=d.get("return_url", ""),
            shopper_email=d.get("shopper_email") or booking.customer_email,
        )
    except Exception as exc:
        return Response({"code": "adyen_error", "message": str(exc)}, status=502)

    payment = Payment.objects.create(
        booking=booking, provider="adyen",
        session_id=session.get("id", ""),
        amount=d["amount"], currency=d["currency"],
        status=PaymentStatus.INITIATED,
        raw=session,
    )
    return Response({
        "payment_id": payment.id,
        "session": session,
        "client_key": settings.ADYEN_CLIENT_KEY,
        "environment": settings.ADYEN_ENV,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_pay_link(request):
    """POST /api/payments/links/ — Admin generates an Adyen Pay By Link."""
    s = CreatePayLinkSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    booking = get_object_or_404(Booking, reference=d["booking_ref"])

    try:
        link = adyen_client.create_pay_by_link(
            reference=booking.reference,
            amount=d["amount"], currency=d["currency"],
            description=d.get("description") or f"Booking {booking.reference}",
            shopper_email=d.get("shopper_email") or booking.customer_email,
        )
    except Exception as exc:
        return Response({"code": "adyen_error", "message": str(exc)}, status=502)

    payment = Payment.objects.create(
        booking=booking, provider="adyen",
        provider_reference=link.get("id", ""),
        payment_link=link.get("url", ""),
        amount=d["amount"], currency=d["currency"],
        status=PaymentStatus.INITIATED,
        raw=link,
    )

    if d.get("send_email") and (d.get("shopper_email") or booking.customer_email):
        try:
            send_mail(
                subject=f"Payment link for booking {booking.reference}",
                message=(
                    f"Hi {booking.customer_name},\n\n"
                    f"Please complete your payment of {d['amount']} {d['currency']} here:\n"
                    f"{link.get('url')}\n\nThank you."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[d.get("shopper_email") or booking.customer_email],
                fail_silently=True,
            )
        except Exception:
            pass

    return Response({"payment_id": payment.id, "url": link.get("url"), "link": link},
                    status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def payment_status(request, ref):
    """GET /api/payments/{provider_reference}/"""
    p = get_object_or_404(Payment, provider_reference=ref)
    return Response({
        "reference": p.provider_reference,
        "amount": str(p.amount),
        "currency": p.currency,
        "status": p.status,
        "booking": p.booking.reference,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def adyen_webhook(request):
    """POST /api/payments/webhooks/adyen/ — HMAC-verified notifications."""
    payload = request.data or {}
    items = payload.get("notificationItems") or []
    results = []
    for wrap in items:
        try:
            if not adyen_client.verify_notification(wrap):
                results.append({"accepted": False, "reason": "bad_hmac"})
                continue
            item = wrap["NotificationRequestItem"]
            code = item.get("eventCode")
            success = str(item.get("success", "false")).lower() == "true"
            merchant_ref = item.get("merchantReference", "")
            psp = item.get("pspReference", "")

            payment = Payment.objects.filter(booking__reference=merchant_ref).order_by("-created_at").first()
            if payment:
                if not payment.provider_reference:
                    payment.provider_reference = psp
                if code == "AUTHORISATION":
                    payment.status = PaymentStatus.AUTHORISED if success else PaymentStatus.FAILED
                elif code == "CAPTURE":
                    payment.status = PaymentStatus.CAPTURED if success else PaymentStatus.FAILED
                elif code == "REFUND":
                    payment.status = PaymentStatus.REFUNDED
                elif code == "CANCELLATION":
                    payment.status = PaymentStatus.CANCELLED
                payment.raw = {**(payment.raw or {}), "last_event": item}
                payment.save(update_fields=["provider_reference", "status", "raw", "updated_at"])

                if payment.status == PaymentStatus.AUTHORISED:
                    payment.booking.status = "confirmed"
                    payment.booking.save(update_fields=["status", "updated_at"])
                    try:
                        send_mail(
                            subject=f"Invoice for booking {payment.booking.reference}",
                            message=(
                                f"Hi {payment.booking.customer_name},\n\n"
                                f"We've received your payment of {payment.amount} {payment.currency} "
                                f"for booking {payment.booking.reference}.\n\nThank you."
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[payment.booking.customer_email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass
            results.append({"accepted": True, "eventCode": code})
        except Exception as exc:
            results.append({"accepted": False, "reason": str(exc)})

    # Adyen expects a plain "[accepted]" body 2xx to acknowledge receipt.
    return Response("[accepted]", status=200)


@api_view(["POST"])
@permission_classes([AllowAny])
def create_public_pay_link(request):
    """
    POST /api/payments/adyen/create-link/

    Public checkout endpoint used by the website right after a booking is
    created. Amount and currency are always taken from the stored booking, so
    the price can never be tampered with from the browser.
    """
    s = PublicPayLinkSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data

    booking = None
    if d.get("booking_id"):
        booking = Booking.objects.filter(pk=d["booking_id"]).first()
    if booking is None:
        ref = d.get("booking_ref") or d.get("reference") or ""
        booking = Booking.objects.filter(reference=ref).first()
    if booking is None:
        return Response({"code": "not_found", "message": "Booking not found", "details": None},
                        status=status.HTTP_404_NOT_FOUND)

    amount = booking.total_amount or Decimal("0")
    if amount <= 0:
        return Response({"code": "validation_error", "message": "Booking has no payable amount",
                         "details": None}, status=status.HTTP_400_BAD_REQUEST)

    try:
        link = adyen_client.create_pay_by_link(
            reference=booking.reference,
            amount=amount,
            currency=booking.currency or d.get("currency", "AED"),
            description=d.get("description") or f"Booking {booking.reference}",
            shopper_email=d.get("customer_email") or booking.customer_email,
        )
    except Exception as exc:
        return Response({"code": "adyen_error", "message": str(exc), "details": None}, status=502)

    payment = Payment.objects.create(
        booking=booking, provider="adyen",
        provider_reference=link.get("id", ""),
        payment_link=link.get("url", ""),
        amount=amount, currency=booking.currency or "AED",
        status=PaymentStatus.INITIATED,
        raw=link,
    )
    return Response(
        {
            "payment_id": payment.id,
            "booking_reference": booking.reference,
            "amount": str(amount),
            "currency": payment.currency,
            "payment_link": link.get("url", ""),
            "url": link.get("url", ""),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def create_public_session(request):
    """
    POST /api/payments/adyen/create-session/

    On-site (Drop-in / Web Components) checkout for a booking that was just
    created by the website. No payment *link* is generated — the customer pays
    on our own /payment/checkout page with card, wallets, UPI, etc.
    Amount and currency always come from the stored booking.
    """
    s = PublicPayLinkSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data

    booking = None
    if d.get("booking_id"):
        booking = Booking.objects.filter(pk=d["booking_id"]).first()
    if booking is None:
        ref = d.get("booking_ref") or d.get("reference") or ""
        booking = Booking.objects.filter(reference=ref).first()
    if booking is None:
        return Response({"code": "not_found", "message": "Booking not found", "details": None},
                        status=status.HTTP_404_NOT_FOUND)

    amount = booking.total_amount or Decimal("0")
    if amount <= 0:
        return Response({"code": "validation_error", "message": "Booking has no payable amount",
                         "details": None}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = adyen_client.create_session(
            reference=booking.reference,
            amount=amount,
            currency=booking.currency or d.get("currency", "AED"),
            country_code="AE",
            return_url=f"{settings.FRONTEND_URL}/payment/return?ref={booking.reference}",
            shopper_email=d.get("customer_email") or booking.customer_email,
        )
    except Exception as exc:
        return Response({"code": "adyen_error", "message": str(exc), "details": None}, status=502)

    payment = Payment.objects.create(
        booking=booking, provider="adyen",
        session_id=session.get("id", ""),
        amount=amount, currency=booking.currency or "AED",
        status=PaymentStatus.INITIATED,
        raw=session,
    )
    return Response({
        "payment_id": payment.id,
        "booking_reference": booking.reference,
        "amount": str(amount),
        "currency": payment.currency,
        "session": session,
        "client_key": settings.ADYEN_CLIENT_KEY,
        "environment": settings.ADYEN_ENV,
    }, status=status.HTTP_201_CREATED)

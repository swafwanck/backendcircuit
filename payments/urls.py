from django.urls import path
from .views import (
    create_session, create_pay_link, payment_status, adyen_webhook,
    create_public_pay_link, create_public_session,
)

urlpatterns = [
    path("payments/sessions/", create_session, name="adyen_create_session"),
    path("payments/links/", create_pay_link, name="adyen_create_pay_link"),
    path("payments/adyen/create-session/", create_public_session, name="adyen_public_session"),
    path("payments/adyen/create-link/", create_public_pay_link, name="adyen_public_pay_link"),
    path("payments/webhooks/adyen/", adyen_webhook, name="adyen_webhook"),
    path("payments/<str:ref>/", payment_status, name="adyen_payment_status"),
]

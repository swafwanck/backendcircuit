from rest_framework import serializers


class CreateSessionSerializer(serializers.Serializer):
    booking_ref = serializers.CharField(max_length=40)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=8, default="AED")
    country_code = serializers.CharField(max_length=4, default="AE")
    return_url = serializers.URLField(required=False, allow_blank=True)
    shopper_email = serializers.EmailField(required=False, allow_blank=True)


class CreatePayLinkSerializer(serializers.Serializer):
    booking_ref = serializers.CharField(max_length=40)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=8, default="AED")
    description = serializers.CharField(required=False, allow_blank=True)
    shopper_email = serializers.EmailField(required=False, allow_blank=True)
    send_email = serializers.BooleanField(default=True)


class PublicPayLinkSerializer(serializers.Serializer):
    """Checkout flow: the website posts the booking it just created."""
    booking_id = serializers.IntegerField(required=False)
    booking_ref = serializers.CharField(max_length=40, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=80, required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=8, default="AED")
    description = serializers.CharField(required=False, allow_blank=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("booking_id") and not (attrs.get("booking_ref") or attrs.get("reference")):
            raise serializers.ValidationError("Provide booking_id or booking_ref.")
        return attrs

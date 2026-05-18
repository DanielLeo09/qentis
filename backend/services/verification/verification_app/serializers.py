from rest_framework import serializers
from .models import VerificationLog, FraudFlag


class VerificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationLog
        fields = [
            'id',
            'item_id',
            'issuer_id',
            'method',
            'result',
            'input_data',
            'verifier_ip',
            'verified_at',
        ]
        read_only_fields = [
            'id',
            'verified_at',
        ]


class FraudFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudFlag
        fields = [
            'id',
            'item_id',
            'issuer_id',
            'verification_count',
            'window_start',
            'window_end',
            'flagged_at',
            'status',
            'resolved_by',
            'resolved_at',
            'resolution_notes',
        ]
        read_only_fields = [
            'id',
            'flagged_at',
            'resolved_at',
        ]


class VerifyQRSerializer(serializers.Serializer):
    qr_data = serializers.CharField(
        required=True,
        help_text="QR code data decoded from scan"
    )


class VerifySerialSerializer(serializers.Serializer):
    serial_number = serializers.CharField(
        required=True,
        help_text="Serial number printed on the item"
    )


class VerifySignatureSerializer(serializers.Serializer):
    document = serializers.FileField(
        required=True,
        help_text="Signed PDF document to verify"
    )


class VerifyOCRSerializer(serializers.Serializer):
    image = serializers.ImageField(
        required=True,
        help_text="Photo of the banknote"
    )


class VerifyWatermarkSerializer(serializers.Serializer):
    image = serializers.ImageField(
        required=True,
        help_text="Photo of the document with watermark"
    )


class VerificationResultSerializer(serializers.Serializer):
    """
    Standard response format for all verification methods.
    """
    result = serializers.ChoiceField(
        choices=VerificationLog.Result.choices
    )
    item_id = serializers.UUIDField(allow_null=True)
    method = serializers.ChoiceField(
        choices=VerificationLog.Method.choices
    )
    message = serializers.CharField()
    item_details = serializers.DictField(allow_null=True)
    verified_at = serializers.DateTimeField()


class ReportItemSerializer(serializers.Serializer):
    item_id = serializers.UUIDField(required=True)
    reason = serializers.CharField(required=True)

    def validate_reason(self, value):
        if len(value) < 10:
            raise serializers.ValidationError(
                "Report reason must be at least 10 characters."
            )
        return value
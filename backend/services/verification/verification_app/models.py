import uuid
from django.db import models


class VerificationLog(models.Model):

    class Method(models.TextChoices):
        QR = 'QR', 'QR Code Scan'
        SERIAL = 'SERIAL', 'Serial Number'
        SIGNATURE = 'SIGNATURE', 'Digital Signature'
        OCR = 'OCR', 'OCR Photo Scan'
        WATERMARK = 'WATERMARK', 'Watermark Detection'

    class Result(models.TextChoices):
        AUTHENTIC = 'AUTHENTIC', 'Authentic'
        NOT_AUTHENTIC = 'NOT_AUTHENTIC', 'Not Authentic'
        UNVERIFIABLE = 'UNVERIFIABLE', 'Unverifiable'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    item_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the item being verified"
    )
    issuer_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the issuer who registered the item"
    )
    method = models.CharField(
        max_length=10,
        choices=Method.choices
    )
    result = models.CharField(
        max_length=15,
        choices=Result.choices
    )
    input_data = models.TextField(
        blank=True,
        help_text="The QR data, serial number, or other input used"
    )
    verifier_ip = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'verification_logs'
        ordering = ['-verified_at']

    def __str__(self):
        return f"{self.method} - {self.result} - {self.verified_at}"


class FraudFlag(models.Model):

    class FlagStatus(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        RESOLVED = 'RESOLVED', 'Resolved'
        DISMISSED = 'DISMISSED', 'Dismissed'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    item_id = models.UUIDField(
        help_text="ID of the suspicious item"
    )
    issuer_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the issuer who registered the item"
    )
    verification_count = models.IntegerField(
        help_text="Number of verifications in the time window"
    )
    window_start = models.DateTimeField(
        help_text="Start of the suspicious time window"
    )
    window_end = models.DateTimeField(
        help_text="End of the suspicious time window"
    )
    flagged_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=FlagStatus.choices,
        default=FlagStatus.OPEN
    )
    resolved_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the admin who resolved this flag"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'fraud_flags'
        ordering = ['-flagged_at']

    def __str__(self):
        return f"Flag - Item {self.item_id} - {self.status}"
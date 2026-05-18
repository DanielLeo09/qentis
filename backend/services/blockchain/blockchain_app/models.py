import uuid
from django.db import models


class BlockchainRecord(models.Model):

    class Category(models.TextChoices):
        ACADEMIC   = 'ACADEMIC',   'Academic Certificate'
        PHARMA     = 'PHARMA',     'Pharmaceutical Product'
        DOCUMENT   = 'DOCUMENT',   'Official Document'
        CURRENCY   = 'CURRENCY',   'Currency / Banknote'

    class Status(models.TextChoices):
        STORED  = 'STORED',  'Stored on blockchain'
        REVOKED = 'REVOKED', 'Revoked'
        PENDING = 'PENDING', 'Pending — blockchain temporarily unreachable'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    item_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA-256 hash of the item details"
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices
    )
    issuer_id = models.CharField(
        max_length=255,
        help_text="UUID of the issuer from the auth service"
    )
    issuer_name = models.CharField(
        max_length=255,
        help_text="Human-readable institution name"
    )
    tx_hash = models.CharField(
        max_length=255,
        blank=True,
        help_text="Ethereum transaction hash returned by Ganache"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.STORED
    )
    revoke_reason = models.TextField(
        blank=True,
        help_text="Reason for revocation if status is REVOKED"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'blockchain_records'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_hash[:16]}... ({self.category}) — {self.status}"
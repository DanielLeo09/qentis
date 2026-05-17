import uuid
from django.db import models


class Institution(models.Model):

    class InstitutionType(models.TextChoices):
        UNIVERSITY = 'UNIVERSITY', 'University'
        HOSPITAL = 'HOSPITAL', 'Hospital'
        NOTARY = 'NOTARY', 'Notary'
        BANK = 'BANK', 'Bank'
        MANUFACTURER = 'MANUFACTURER', 'Manufacturer'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        REVOKED = 'REVOKED', 'Revoked'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user_id = models.UUIDField(
        unique=True,
        help_text="ID of the user from User & Auth Service"
    )
    name = models.CharField(max_length=255)
    institution_type = models.CharField(
        max_length=20,
        choices=InstitutionType.choices
    )
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    contact_email = models.EmailField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    approved_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the admin who approved or rejected"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'institutions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"


class InstitutionDocument(models.Model):

    class DocumentType(models.TextChoices):
        ACCREDITATION = 'ACCREDITATION', 'Accreditation Certificate'
        REGISTRATION = 'REGISTRATION', 'Registration Paper'
        LICENSE = 'LICENSE', 'Operating License'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file_path = models.FileField(
        upload_to='institution_documents/'
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'institution_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.institution.name} - {self.document_type}"
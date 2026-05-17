from rest_framework import serializers
from .models import Institution, InstitutionDocument


class InstitutionDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = InstitutionDocument
        fields = [
            'id',
            'document_type',
            'file_path',
            'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']


class InstitutionSerializer(serializers.ModelSerializer):
    documents = InstitutionDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Institution
        fields = [
            'id',
            'user_id',
            'name',
            'institution_type',
            'country',
            'city',
            'contact_email',
            'status',
            'approved_by',
            'approved_at',
            'rejection_reason',
            'created_at',
            'updated_at',
            'documents'
        ]
        read_only_fields = [
            'id',
            'user_id',
            'status',
            'approved_by',
            'approved_at',
            'created_at',
            'updated_at'
        ]


class InstitutionApplySerializer(serializers.ModelSerializer):
    """
    Used when an issuer submits a new application.
    Only accepts the fields the issuer can fill in.
    """
    class Meta:
        model = Institution
        fields = [
            'name',
            'institution_type',
            'country',
            'city',
            'contact_email',
        ]

    def validate_contact_email(self, value):
        if not value:
            raise serializers.ValidationError(
                "Contact email is required."
            )
        return value.lower()

    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError(
                "Institution name must be at least 3 characters."
            )
        return value


class InstitutionStatusSerializer(serializers.ModelSerializer):
    """
    Used when admin approves or rejects.
    Only admin can set these fields.
    """
    class Meta:
        model = Institution
        fields = [
            'id',
            'name',
            'status',
            'approved_by',
            'approved_at',
            'rejection_reason',
        ]
        read_only_fields = [
            'id',
            'name',
            'approved_by',
            'approved_at',
        ]


class AdminInstitutionSerializer(serializers.ModelSerializer):
    """
    Full institution details for admin view
    including all documents submitted.
    """
    documents = InstitutionDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Institution
        fields = '__all__'
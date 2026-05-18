from rest_framework import serializers
from .models import BlockchainRecord


class StoreHashSerializer(serializers.Serializer):
    """
    Validates the data coming in when a new item hash is stored.
    Called by the Item Registration Service.
    """
    item_hash   = serializers.CharField(max_length=64)
    category    = serializers.ChoiceField(choices=BlockchainRecord.Category.choices)
    issuer_id   = serializers.CharField(max_length=255)
    issuer_name = serializers.CharField(max_length=255)


class VerifyHashSerializer(serializers.Serializer):
    """
    Validates the hash coming in for verification.
    Called by the Verification Service.
    """
    item_hash = serializers.CharField(max_length=64)


class RevokeHashSerializer(serializers.Serializer):
    """
    Validates revocation requests.
    Called by the Item Registration Service when an issuer revokes an item.
    """
    item_hash = serializers.CharField(max_length=64)
    reason    = serializers.CharField(max_length=500)


class BlockchainRecordSerializer(serializers.ModelSerializer):
    """
    Serializes a full BlockchainRecord for display.
    """
    class Meta:
        model  = BlockchainRecord
        fields = [
            'id',
            'item_hash',
            'category',
            'issuer_id',
            'issuer_name',
            'tx_hash',
            'status',
            'revoke_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
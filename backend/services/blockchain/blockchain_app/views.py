from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import BlockchainRecord
from .serializers import (
    StoreHashSerializer,
    VerifyHashSerializer,
    RevokeHashSerializer,
    BlockchainRecordSerializer,
)
from .contract import (
    store_hash_on_chain,
    verify_hash_on_chain,
    revoke_hash_on_chain,
)


@api_view(['POST'])
@permission_classes([AllowAny])
def store_hash(request):
    """
    Store a new item hash on the blockchain.
    POST /api/blockchain/store/
    Called by the Item Registration Service.
    """
    serializer = StoreHashSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data      = serializer.validated_data
    item_hash = data['item_hash']

    # Check if this hash already exists in our database
    if BlockchainRecord.objects.filter(item_hash=item_hash).exists():
        return Response(
            {'error': 'This hash is already registered.'},
            status=status.HTTP_409_CONFLICT
        )

    try:
        tx_hash = store_hash_on_chain(
            item_hash   = item_hash,
            category    = data['category'],
            issuer_id   = data['issuer_id'],
            issuer_name = data['issuer_name'],
        )

        # Save a local record in PostgreSQL as backup
        record = BlockchainRecord.objects.create(
            item_hash   = item_hash,
            category    = data['category'],
            issuer_id   = data['issuer_id'],
            issuer_name = data['issuer_name'],
            tx_hash     = tx_hash,
            status      = BlockchainRecord.Status.STORED,
        )

        return Response(
            {
                'message':  'Hash stored on blockchain successfully.',
                'tx_hash':  tx_hash,
                'record':   BlockchainRecordSerializer(record).data,
            },
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        return Response(
            {'error': f'Blockchain error: {str(e)}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_hash(request):
    """
    Verify a hash against the blockchain.
    POST /api/blockchain/verify/
    Called by the Verification Service.
    """
    serializer = VerifyHashSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    item_hash = serializer.validated_data['item_hash']

    try:
        result = verify_hash_on_chain(item_hash)

        if not result['exists']:
            return Response(
                {
                    'status':  'NOT_AUTHENTIC',
                    'message': 'No record found for this hash on the blockchain.',
                },
                status=status.HTTP_200_OK
            )

        if result['revoked']:
            return Response(
                {
                    'status':        'NOT_AUTHENTIC',
                    'message':       'This item has been revoked by the issuer.',
                    'revoke_reason': result['revoke_reason'],
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                'status':      'AUTHENTIC',
                'item_hash':   item_hash,
                'category':    result['category'],
                'issuer_id':   result['issuer_id'],
                'issuer_name': result['issuer_name'],
                'timestamp':   result['timestamp'],
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': f'Blockchain error: {str(e)}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def revoke_hash(request):
    """
    Revoke an item hash on the blockchain.
    POST /api/blockchain/revoke/
    Called by the Item Registration Service when an issuer revokes an item.
    """
    serializer = RevokeHashSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    item_hash = serializer.validated_data['item_hash']
    reason    = serializer.validated_data['reason']

    try:
        record = BlockchainRecord.objects.get(item_hash=item_hash)
    except BlockchainRecord.DoesNotExist:
        return Response(
            {'error': 'Hash not found in local records.'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        tx_hash = revoke_hash_on_chain(item_hash, reason)

        record.status        = BlockchainRecord.Status.REVOKED
        record.revoke_reason = reason
        record.tx_hash       = tx_hash
        record.save()

        return Response(
            {
                'message':  'Item revoked successfully.',
                'tx_hash':  tx_hash,
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': f'Blockchain error: {str(e)}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint.
    GET /api/blockchain/health/
    Used by Docker and Kubernetes to confirm the service is running.
    """
    try:
        from .web3_client import get_web3
        w3 = get_web3()
        connected = w3.is_connected()
    except Exception:
        connected = False

    return Response(
        {
            'service':           'blockchain',
            'status':            'ok',
            'ganache_connected': connected,
            'total_records':     BlockchainRecord.objects.count(),
        },
        status=status.HTTP_200_OK
    )
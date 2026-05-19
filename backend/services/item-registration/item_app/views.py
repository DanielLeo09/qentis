import uuid
import hashlib
import requests
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import (
    Item,
    CertificateDetail,
    PharmaceuticalDetail,
    DocumentDetail,
    BanknoteDetail,
)
from .serializers import (
    ItemSerializer,
    RegisterItemSerializer,
    RevokeItemSerializer,
)


def generate_hash(field_values):
    """Generate SHA-256 hash from concatenated field values."""
    return hashlib.sha256(field_values.encode()).hexdigest()


def call_blockchain_service(item_id, category, hash_fields, issuer_id=None, issuer_name=None):
    """
    Call Blockchain Service to store hash on Ethereum.
    Generates SHA-256 hash here and sends it to Blockchain Service.
    Falls back to mock if service not available.
    """
    item_hash = generate_hash(hash_fields)

    try:
        response = requests.post(
            f"{settings.BLOCKCHAIN_SERVICE_URL}/api/blockchain/store/",
            json={
                'item_hash':   item_hash,
                'category':    category,
                'issuer_id':   str(issuer_id) if issuer_id else 'unknown',
                'issuer_name': issuer_name or 'Unknown Institution',
            },
            timeout=10
        )
        if response.status_code == 201:
            data = response.json()
            return {
                'hash': item_hash,
                'transaction_hash': data.get('tx_hash', ''),
            }
    except Exception:
        pass

    # MOCK RESPONSE — fallback only
    return {
        'hash': item_hash,
        'transaction_hash': f'mock-tx-{str(item_id)[:8]}',
    }


def call_output_service(item_id, category):
    """
    Call Auth Output Service to generate QR code and serial number.
    SPRINT 1: Returns mock response.
    SPRINT 2: Replace with real HTTP call.
    """
    try:
        response = requests.post(
            f"{settings.OUTPUT_SERVICE_URL}/api/outputs/generate/",
            json={
                'item_id': str(item_id),
                'category': category,
            },
            timeout=10
        )
        if response.status_code == 201:
            return response.json()
    except Exception:
        pass

    # MOCK RESPONSE — Sprint 1 only
    return {
        'qr_code_url': f'http://localhost:8005/media/qr/{item_id}.png',
        'serial_number': f'QNT-{timezone.now().year}-{category[:4]}-{str(item_id)[:8].upper()}',
    }


def create_detail(item, category, data):
    """
    Create the category-specific detail record.
    """
    if category == Item.Category.CERTIFICATE:
        detail = CertificateDetail.objects.create(
            item=item,
            student_name=data['student_name'],
            matricule=data['matricule'],
            degree=data['degree'],
            institution_name=data['institution_name'],
            graduation_date=data['graduation_date'],
            grade=data['grade'],
        )
    elif category == Item.Category.PHARMACEUTICAL:
        detail = PharmaceuticalDetail.objects.create(
            item=item,
            drug_name=data['drug_name'],
            batch_number=data['batch_number'],
            manufacturer=data['manufacturer'],
            production_date=data['production_date'],
            expiry_date=data['expiry_date'],
            factory_location=data['factory_location'],
        )
    elif category == Item.Category.DOCUMENT:
        detail = DocumentDetail.objects.create(
            item=item,
            document_type=data['document_type'],
            owner_name=data['owner_name'],
            issuing_authority=data['issuing_authority'],
            reference_number=data['reference_number'],
            location=data['location'],
            issue_date=data['issue_date'],
        )
    elif category == Item.Category.BANKNOTE:
        detail = BanknoteDetail.objects.create(
            item=item,
            currency=data['currency'],
            denomination=data['denomination'],
            serial_number=data['serial_number'],
            series=data['series'],
            issue_date=data['issue_date'],
            issuing_bank=data['issuing_bank'],
        )
    return detail


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_item(request):
    """
    Issuer registers a new item for authentication.
    POST /api/items/register/
    JWT required — must be ISSUER role.
    """
    issuer_id = request.META.get('HTTP_X_USER_ID')
    role = request.META.get('HTTP_X_USER_ROLE')

    if not issuer_id:
        return Response(
            {'error': 'User ID not found in request headers.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if role != 'ISSUER':
        return Response(
            {'error': 'Only issuers can register items.'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = RegisterItemSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    data = serializer.validated_data
    category = data['category']

    # Create the Item record
    item = Item.objects.create(
        issuer_id=uuid.UUID(issuer_id),
        institution_id=uuid.UUID(
            request.data.get('institution_id', str(uuid.uuid4()))
        ),
        category=category,
        status=Item.Status.REGISTERED,
    )

    # Create the category-specific detail record
    detail = create_detail(item, category, data)

    # Get hash fields from detail model
    hash_fields = detail.get_hash_fields()

    # Call Blockchain Service
    blockchain_response = call_blockchain_service(
        item.id, category, hash_fields,
        issuer_id=issuer_id,
        issuer_name=request.data.get('institution_name', 'Unknown Institution')
    )

    # Call Auth Output Service (mock in Sprint 1)
    output_response = call_output_service(item.id, category)

    # Update item with blockchain and output data
    item.blockchain_hash = blockchain_response.get('hash')
    item.transaction_hash = blockchain_response.get('transaction_hash')
    item.qr_code_url = output_response.get('qr_code_url')
    item.serial_number = output_response.get('serial_number')
    item.save()

    serializer = ItemSerializer(item)
    return Response(
        {
            'message': 'Item registered successfully.',
            'item': serializer.data,
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_items(request):
    """
    Issuer views all their registered items.
    GET /api/items/my-items/
    JWT required.
    """
    issuer_id = request.META.get('HTTP_X_USER_ID')

    if not issuer_id:
        return Response(
            {'error': 'User ID not found in request headers.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    items = Item.objects.filter(issuer_id=issuer_id)
    serializer = ItemSerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def item_detail(request, item_id):
    """
    Get full details of one item.
    GET /api/items/{item_id}/
    JWT required.
    """
    issuer_id = request.META.get('HTTP_X_USER_ID')
    role = request.META.get('HTTP_X_USER_ROLE')

    try:
        if role == 'ADMIN':
            item = Item.objects.get(id=item_id)
        else:
            item = Item.objects.get(id=item_id, issuer_id=issuer_id)
    except Item.DoesNotExist:
        return Response(
            {'error': 'Item not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = ItemSerializer(item)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def revoke_item(request, item_id):
    """
    Issuer revokes a registered item.
    PUT /api/items/{item_id}/revoke/
    JWT required — must be the issuer who registered the item.
    """
    issuer_id = request.META.get('HTTP_X_USER_ID')

    if not issuer_id:
        return Response(
            {'error': 'User ID not found in request headers.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        item = Item.objects.get(id=item_id, issuer_id=issuer_id)
    except Item.DoesNotExist:
        return Response(
            {'error': 'Item not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if item.status == Item.Status.REVOKED:
        return Response(
            {'error': 'Item is already revoked.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = RevokeItemSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    item.status = Item.Status.REVOKED
    item.revoked_at = timezone.now()
    item.revoke_reason = serializer.validated_data['reason']
    item.save()

    return Response(
        {
            'message': 'Item revoked successfully.',
            'item_id': str(item.id),
            'status': item.status,
            'revoked_at': item.revoked_at,
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def all_items(request):
    """
    Admin views all registered items.
    GET /api/items/all/
    Admin JWT required.
    """
    role = request.META.get('HTTP_X_USER_ROLE')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can view all items.'},
            status=status.HTTP_403_FORBIDDEN
        )

    category = request.query_params.get('category')
    status_filter = request.query_params.get('status')

    items = Item.objects.all()

    if category:
        items = items.filter(category=category)
    if status_filter:
        items = items.filter(status=status_filter)

    serializer = ItemSerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
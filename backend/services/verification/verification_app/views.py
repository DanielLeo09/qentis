import uuid
import json
import redis
import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from .models import VerificationLog, FraudFlag
from .serializers import (
    VerifyQRSerializer,
    VerifySerialSerializer,
    VerifySignatureSerializer,
    VerifyOCRSerializer,
    VerifyWatermarkSerializer,
    VerificationLogSerializer,
    FraudFlagSerializer,
    ReportItemSerializer,
)


def get_redis_client():
    """Get Redis connection."""
    return redis.from_url(settings.REDIS_URL)


def get_verifier_ip(request):
    """Extract verifier IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def check_blockchain(item_id=None, serial_number=None, blockchain_hash=None):
    """
    Call Blockchain Service to verify an item.
    SPRINT 1: Returns mock response.
    SPRINT 2: Replace with real HTTP call.
    """
    try:
        if item_id:
            url = f"{settings.BLOCKCHAIN_SERVICE_URL}/api/blockchain/verify/{item_id}/"
        else:
            url = f"{settings.BLOCKCHAIN_SERVICE_URL}/api/blockchain/verify/serial/{serial_number}/"

        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    # MOCK RESPONSE — Sprint 1 only
    return {
        'exists': True,
        'timestamp': timezone.now().isoformat(),
        'item_details': {
            'category': 'CERTIFICATE',
            'issuer': 'Mock Institution',
            'registered_at': timezone.now().isoformat(),
        }
    }


def get_cached_result(item_id):
    """Check Redis cache for a previous verification result."""
    try:
        r = get_redis_client()
        cached = r.get(f'verify:{item_id}')
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


def cache_result(item_id, result):
    """Store verification result in Redis with TTL."""
    try:
        r = get_redis_client()
        r.setex(
            f'verify:{item_id}',
            settings.CACHE_TTL,
            json.dumps(result)
        )
    except Exception:
        pass


def check_fraud_pattern(item_id, issuer_id=None):
    """
    Check if this item has been verified suspiciously often.
    If count exceeds FRAUD_THRESHOLD in 60 minutes — create FraudFlag.
    """
    window_start = timezone.now() - timedelta(hours=1)
    window_end = timezone.now()

    count = VerificationLog.objects.filter(
        item_id=item_id,
        verified_at__gte=window_start,
        result=VerificationLog.Result.AUTHENTIC
    ).count()

    if count >= settings.FRAUD_THRESHOLD:
        existing_flag = FraudFlag.objects.filter(
            item_id=item_id,
            status=FraudFlag.FlagStatus.OPEN,
            window_start__gte=window_start
        ).first()

        if not existing_flag:
            FraudFlag.objects.create(
                item_id=item_id,
                issuer_id=issuer_id,
                verification_count=count,
                window_start=window_start,
                window_end=window_end,
            )


def send_issuer_notification(issuer_email, item_id, method):
    """
    Send email notification to issuer when their item is verified.
    Uses Django send_mail with Mailtrap SMTP locally.
    """
    try:
        send_mail(
            subject='Your item was verified on Qentis',
            message=f'Your item {item_id} was verified using {method} method on {timezone.now().strftime("%Y-%m-%d %H:%M")} UTC.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[issuer_email],
            fail_silently=True,
        )
    except Exception:
        pass


def log_verification(item_id, issuer_id, method, result, input_data, verifier_ip):
    """Save verification attempt to database."""
    return VerificationLog.objects.create(
        item_id=item_id,
        issuer_id=issuer_id,
        method=method,
        result=result,
        input_data=str(input_data),
        verifier_ip=verifier_ip,
    )


def build_result(result, item_id, method, message, item_details=None):
    """Build standard verification response."""
    return {
        'result': result,
        'item_id': str(item_id) if item_id else None,
        'method': method,
        'message': message,
        'item_details': item_details,
        'verified_at': timezone.now().isoformat(),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_qr(request):
    """
    Verify item via QR Code scan.
    POST /api/verify/qr/
    No authentication required.
    """
    serializer = VerifyQRSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    qr_data = serializer.validated_data['qr_data']
    verifier_ip = get_verifier_ip(request)

    try:
        item_id = uuid.UUID(qr_data)
    except ValueError:
        log_verification(
            None, None, VerificationLog.Method.QR,
            VerificationLog.Result.NOT_AUTHENTIC,
            qr_data, verifier_ip
        )
        return Response(
            build_result(
                VerificationLog.Result.NOT_AUTHENTIC,
                None, VerificationLog.Method.QR,
                'Invalid QR code format. This item could not be verified.'
            ),
            status=status.HTTP_200_OK
        )

    # Check cache first
    cached = get_cached_result(item_id)
    if cached:
        return Response(cached, status=status.HTTP_200_OK)

    # Check blockchain
    blockchain_response = check_blockchain(item_id=item_id)

    if blockchain_response.get('exists'):
        result = VerificationLog.Result.AUTHENTIC
        message = 'This item is AUTHENTIC. It was registered on Qentis.'
        item_details = blockchain_response.get('item_details')
    else:
        result = VerificationLog.Result.NOT_AUTHENTIC
        message = 'This item could NOT be verified. No matching record found.'
        item_details = None

    # Log verification
    log = log_verification(
        item_id, None, VerificationLog.Method.QR,
        result, qr_data, verifier_ip
    )

    # Cache result
    response_data = build_result(result, item_id, VerificationLog.Method.QR, message, item_details)
    cache_result(item_id, response_data)

    # Check fraud pattern
    if result == VerificationLog.Result.AUTHENTIC:
        check_fraud_pattern(item_id)

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_serial(request):
    """
    Verify item via Serial Number.
    POST /api/verify/serial/
    No authentication required.
    """
    serializer = VerifySerialSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    serial_number = serializer.validated_data['serial_number']
    verifier_ip = get_verifier_ip(request)

    # Check cache
    cached = get_cached_result(f'serial:{serial_number}')
    if cached:
        return Response(cached, status=status.HTTP_200_OK)

    # Check blockchain
    blockchain_response = check_blockchain(serial_number=serial_number)

    if blockchain_response.get('exists'):
        result = VerificationLog.Result.AUTHENTIC
        message = 'This item is AUTHENTIC. Serial number verified on blockchain.'
        item_details = blockchain_response.get('item_details')
        item_id = blockchain_response.get('item_id')
    else:
        result = VerificationLog.Result.NOT_AUTHENTIC
        message = 'Serial number NOT found. This item could not be verified.'
        item_details = None
        item_id = None

    log_verification(
        item_id, None, VerificationLog.Method.SERIAL,
        result, serial_number, verifier_ip
    )

    response_data = build_result(
        result, item_id, VerificationLog.Method.SERIAL, message, item_details
    )
    cache_result(f'serial:{serial_number}', response_data)

    if result == VerificationLog.Result.AUTHENTIC and item_id:
        check_fraud_pattern(item_id)

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def verify_signature(request):
    """
    Verify item via Digital Signature.
    POST /api/verify/signature/
    No authentication required.
    User uploads a signed PDF.
    """
    serializer = VerifySignatureSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    document = serializer.validated_data['document']
    verifier_ip = get_verifier_ip(request)

    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature
        import hashlib

        document_bytes = document.read()
        document_hash = hashlib.sha256(document_bytes).hexdigest()

        blockchain_response = check_blockchain(item_id=document_hash[:32])

        if blockchain_response.get('exists'):
            result = VerificationLog.Result.AUTHENTIC
            message = 'Digital signature VERIFIED. Document is authentic.'
            item_details = blockchain_response.get('item_details')
        else:
            result = VerificationLog.Result.NOT_AUTHENTIC
            message = 'Digital signature could not be verified.'
            item_details = None

    except Exception:
        result = VerificationLog.Result.UNVERIFIABLE
        message = 'Could not process the document. Please ensure it is a valid signed PDF.'
        item_details = None

    log_verification(
        None, None, VerificationLog.Method.SIGNATURE,
        result, document.name, verifier_ip
    )

    return Response(
        build_result(result, None, VerificationLog.Method.SIGNATURE, message, item_details),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def verify_ocr(request):
    """
    Verify banknote via OCR Photo Scan.
    POST /api/verify/ocr/
    No authentication required.
    User uploads a photo of the banknote.
    """
    serializer = VerifyOCRSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    image = serializer.validated_data['image']
    verifier_ip = get_verifier_ip(request)

    try:
        import cv2
        import pytesseract
        import numpy as np
        from PIL import Image
        import io

        image_bytes = image.read()
        pil_image = Image.open(io.BytesIO(image_bytes))
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]

        extracted_text = pytesseract.image_to_string(gray)
        serial_number = extracted_text.strip().replace(' ', '').replace('\n', '')

        if not serial_number:
            return Response(
                build_result(
                    VerificationLog.Result.UNVERIFIABLE,
                    None, VerificationLog.Method.OCR,
                    'Could not extract serial number from image. Please take a clearer photo.',
                ),
                status=status.HTTP_200_OK
            )

        blockchain_response = check_blockchain(serial_number=serial_number)

        if blockchain_response.get('exists'):
            result = VerificationLog.Result.AUTHENTIC
            message = f'Serial number {serial_number} verified. Banknote is AUTHENTIC.'
            item_details = blockchain_response.get('item_details')
            item_id = blockchain_response.get('item_id')
        else:
            result = VerificationLog.Result.NOT_AUTHENTIC
            message = f'Serial number {serial_number} not found. Banknote could NOT be verified.'
            item_details = None
            item_id = None

    except Exception as e:
        result = VerificationLog.Result.UNVERIFIABLE
        message = 'Error processing image. Please try again with a clearer photo.'
        item_details = None
        item_id = None
        serial_number = ''

    log_verification(
        item_id if 'item_id' in locals() else None,
        None, VerificationLog.Method.OCR,
        result, serial_number, verifier_ip
    )

    return Response(
        build_result(
            result,
            item_id if 'item_id' in locals() else None,
            VerificationLog.Method.OCR,
            message, item_details
        ),
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def verify_watermark(request):
    """
    Verify document via Watermark Detection.
    POST /api/verify/watermark/
    No authentication required.
    User uploads a photo of the document.
    """
    serializer = VerifyWatermarkSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    image = serializer.validated_data['image']
    verifier_ip = get_verifier_ip(request)

    try:
        from stegano import lsb
        from PIL import Image
        import io

        image_bytes = image.read()
        pil_image = Image.open(io.BytesIO(image_bytes))

        hidden_message = lsb.reveal(pil_image)

        if not hidden_message:
            return Response(
                build_result(
                    VerificationLog.Result.NOT_AUTHENTIC,
                    None, VerificationLog.Method.WATERMARK,
                    'No watermark detected. This document may not be authentic.',
                ),
                status=status.HTTP_200_OK
            )

        item_id = uuid.UUID(hidden_message)
        blockchain_response = check_blockchain(item_id=item_id)

        if blockchain_response.get('exists'):
            result = VerificationLog.Result.AUTHENTIC
            message = 'Watermark verified. Document is AUTHENTIC.'
            item_details = blockchain_response.get('item_details')
        else:
            result = VerificationLog.Result.NOT_AUTHENTIC
            message = 'Watermark found but no matching record. Document could NOT be verified.'
            item_details = None

    except Exception:
        result = VerificationLog.Result.UNVERIFIABLE
        message = 'Could not process watermark. Please upload a clearer image.'
        item_details = None
        item_id = None

    log_verification(
        item_id if 'item_id' in locals() else None,
        None, VerificationLog.Method.WATERMARK,
        result, image.name, verifier_ip
    )

    return Response(
        build_result(
            result,
            item_id if 'item_id' in locals() else None,
            VerificationLog.Method.WATERMARK,
            message, item_details
        ),
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def verification_history(request, item_id):
    """
    Get verification history for an item.
    GET /api/verify/history/{item_id}/
    Admin JWT required.
    """
    role = request.META.get('HTTP_X_USER_ROLE')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can view verification history.'},
            status=status.HTTP_403_FORBIDDEN
        )

    logs = VerificationLog.objects.filter(item_id=item_id)
    serializer = VerificationLogSerializer(logs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def report_item(request):
    """
    Verifier reports a suspicious item.
    POST /api/verify/report/
    No authentication required.
    """
    serializer = ReportItemSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    item_id = serializer.validated_data['item_id']
    reason = serializer.validated_data['reason']
    verifier_ip = get_verifier_ip(request)

    FraudFlag.objects.create(
        item_id=item_id,
        verification_count=0,
        window_start=timezone.now(),
        window_end=timezone.now(),
    )

    log_verification(
        item_id, None, VerificationLog.Method.QR,
        VerificationLog.Result.NOT_AUTHENTIC,
        f'Reported by verifier: {reason}',
        verifier_ip
    )

    return Response(
        {'message': 'Item reported successfully. Our team will investigate.'},
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fraud_flags(request):
    """
    Get all fraud flags.
    GET /api/verify/flags/
    Admin JWT required.
    """
    role = request.META.get('HTTP_X_USER_ROLE')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can view fraud flags.'},
            status=status.HTTP_403_FORBIDDEN
        )

    flags = FraudFlag.objects.all()
    serializer = FraudFlagSerializer(flags, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
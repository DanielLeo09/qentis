import uuid
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Institution, InstitutionDocument
from .serializers import (
    InstitutionSerializer,
    InstitutionApplySerializer,
    InstitutionStatusSerializer,
    AdminInstitutionSerializer,
)


def get_user_from_token(request):
    """
    Extract user information from the JWT token.
    The token is validated by SimpleJWT automatically.
    We read the user_id from the token payload.
    """
    return {
        'user_id': str(request.user.id) if hasattr(request, 'user') else None,
        'role': getattr(request.user, 'role', None)
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply(request):
    """
    Issuer submits institution application.
    POST /api/institution/apply/
    JWT token required — must be an ISSUER role.
    """
    user_id = request.META.get('HTTP_X_USER_ID')

    if not user_id:
        return Response(
            {'error': 'User ID not found in request headers.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if this user already has an application
    existing = Institution.objects.filter(user_id=user_id).first()
    if existing:
        return Response(
            {
                'error': 'You already have an application.',
                'status': existing.status,
                'application_id': str(existing.id)
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = InstitutionApplySerializer(data=request.data)
    if serializer.is_valid():
        institution = serializer.save(
            user_id=uuid.UUID(user_id),
            status=Institution.Status.PENDING
        )

        # Handle document uploads
        documents = request.FILES.getlist('documents')
        doc_type = request.data.get('document_type', 'OTHER')
        for doc in documents:
            InstitutionDocument.objects.create(
                institution=institution,
                file_path=doc,
                document_type=doc_type
            )

        return Response(
            {
                'message': 'Application submitted successfully.',
                'application_id': str(institution.id),
                'status': institution.status,
            },
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def application_status(request):
    """
    Issuer checks their own application status.
    GET /api/institution/status/
    JWT token required.
    """
    user_id = request.META.get('HTTP_X_USER_ID')

    if not user_id:
        return Response(
            {'error': 'User ID not found in request headers.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    institution = Institution.objects.filter(
        user_id=user_id
    ).first()

    if not institution:
        return Response(
            {'error': 'No application found for this user.'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = InstitutionSerializer(institution)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_applications(request):
    """
    Admin views all pending applications.
    GET /api/institution/pending/
    Admin JWT required.
    """
    role = request.META.get('HTTP_X_USER_ROLE')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can view pending applications.'},
            status=status.HTTP_403_FORBIDDEN
        )

    institutions = Institution.objects.filter(
        status=Institution.Status.PENDING
    )
    serializer = AdminInstitutionSerializer(institutions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_institutions(request):
    """
    Admin views all institutions.
    GET /api/institution/all/
    Admin JWT required.
    """
    role = request.META.get('HTTP_X_USER_ROLE')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can view all institutions.'},
            status=status.HTTP_403_FORBIDDEN
        )

    institutions = Institution.objects.all()
    serializer = AdminInstitutionSerializer(institutions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def approve_institution(request, institution_id):
    """
    Admin approves an institution application.
    PUT /api/institution/{id}/approve/
    Admin JWT required.
    """
    role = request.META.get('HTTP_X_USER_ROLE')
    admin_id = request.META.get('HTTP_X_USER_ID')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can approve institutions.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        institution = Institution.objects.get(id=institution_id)
    except Institution.DoesNotExist:
        return Response(
            {'error': 'Institution not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if institution.status != Institution.Status.PENDING:
        return Response(
            {'error': f'Institution is already {institution.status}.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    institution.status = Institution.Status.APPROVED
    institution.approved_by = uuid.UUID(admin_id)
    institution.approved_at = timezone.now()
    institution.save()

    serializer = InstitutionSerializer(institution)
    return Response(
        {
            'message': 'Institution approved successfully.',
            'institution': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def reject_institution(request, institution_id):
    """
    Admin rejects an institution application.
    PUT /api/institution/{id}/reject/
    Admin JWT required — must provide rejection reason.
    """
    role = request.META.get('HTTP_X_USER_ROLE')
    admin_id = request.META.get('HTTP_X_USER_ID')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can reject institutions.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        institution = Institution.objects.get(id=institution_id)
    except Institution.DoesNotExist:
        return Response(
            {'error': 'Institution not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    reason = request.data.get('reason')
    if not reason:
        return Response(
            {'error': 'Rejection reason is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    institution.status = Institution.Status.REJECTED
    institution.approved_by = uuid.UUID(admin_id)
    institution.approved_at = timezone.now()
    institution.rejection_reason = reason
    institution.save()

    serializer = InstitutionSerializer(institution)
    return Response(
        {
            'message': 'Institution rejected.',
            'institution': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def revoke_institution(request, institution_id):
    """
    Admin revokes an approved institution.
    PUT /api/institution/{id}/revoke/
    Admin JWT required — must provide revocation reason.
    """
    role = request.META.get('HTTP_X_USER_ROLE')
    admin_id = request.META.get('HTTP_X_USER_ID')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can revoke institutions.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        institution = Institution.objects.get(id=institution_id)
    except Institution.DoesNotExist:
        return Response(
            {'error': 'Institution not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if institution.status != Institution.Status.APPROVED:
        return Response(
            {'error': 'Only approved institutions can be revoked.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    reason = request.data.get('reason')
    if not reason:
        return Response(
            {'error': 'Revocation reason is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    institution.status = Institution.Status.REVOKED
    institution.approved_by = uuid.UUID(admin_id)
    institution.rejection_reason = reason
    institution.save()

    serializer = InstitutionSerializer(institution)
    return Response(
        {
            'message': 'Institution revoked.',
            'institution': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def institution_detail(request, institution_id):
    """
    Get full details of one institution.
    GET /api/institution/{id}/
    Admin JWT required.
    """
    role = request.META.get('HTTP_X_USER_ROLE')

    if role != 'ADMIN':
        return Response(
            {'error': 'Only administrators can view institution details.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        institution = Institution.objects.get(id=institution_id)
    except Institution.DoesNotExist:
        return Response(
            {'error': 'Institution not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = AdminInstitutionSerializer(institution)
    return Response(serializer.data, status=status.HTTP_200_OK)
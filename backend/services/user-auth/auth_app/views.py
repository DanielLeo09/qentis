import uuid
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import User, Issuer, Verifier, Administrator
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    UpdateProfileSerializer,
    ChangePasswordSerializer,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['user_id'] = str(user.id)
    refresh['email'] = user.email
    refresh['role'] = user.role
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@swagger_auto_schema(
    method='post',
    request_body=RegisterSerializer,
    responses={201: 'Account created successfully'}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user account.
    POST /api/auth/register/
    No authentication required.
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response(
            {
                'message': 'Account created successfully.',
                'user': UserSerializer(user).data,
                'tokens': tokens,
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'password'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
        }
    ),
    responses={200: 'Login successful'}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login with email and password.
    POST /api/auth/login/
    No authentication required.
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {'error': 'Email and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=email.lower(), password=password)

    if not user:
        return Response(
            {'error': 'Invalid email or password.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'error': 'This account has been deactivated.'},
            status=status.HTTP_403_FORBIDDEN
        )

    tokens = get_tokens_for_user(user)
    return Response(
        {
            'message': 'Login successful.',
            'user': UserSerializer(user).data,
            'tokens': tokens,
        },
        status=status.HTTP_200_OK
    )


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['refresh_token'],
        properties={
            'refresh_token': openapi.Schema(type=openapi.TYPE_STRING),
        }
    ),
    responses={200: 'Logged out successfully'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout — blacklist the refresh token.
    POST /api/auth/logout/
    JWT required.
    """
    refresh_token = request.data.get('refresh_token')

    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {'message': 'Logged out successfully.'},
            status=status.HTTP_200_OK
        )
    except TokenError:
        return Response(
            {'error': 'Invalid or expired token.'},
            status=status.HTTP_400_BAD_REQUEST
        )


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['refresh_token'],
        properties={
            'refresh_token': openapi.Schema(type=openapi.TYPE_STRING),
        }
    ),
    responses={200: 'New access token returned'}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Get a new access token using refresh token.
    POST /api/auth/token/refresh/
    No authentication required.
    """
    refresh_token = request.data.get('refresh_token')

    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        token = RefreshToken(refresh_token)
        return Response(
            {'access': str(token.access_token)},
            status=status.HTTP_200_OK
        )
    except TokenError:
        return Response(
            {'error': 'Invalid or expired refresh token.'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Get current user profile.
    GET /api/auth/profile/
    JWT required.
    """
    user = request.user
    serializer = UserSerializer(user)
    data = serializer.data

    if user.role == User.Role.ISSUER and hasattr(user, 'issuer_profile'):
        issuer = user.issuer_profile
        data['issuer_profile'] = {
            'institution_name': issuer.institution_name,
            'institution_type': issuer.institution_type,
            'country': issuer.country,
            'city': issuer.city,
            'contact_email': issuer.contact_email,
        }

    if user.role == User.Role.ADMIN and hasattr(user, 'admin_profile'):
        admin = user.admin_profile
        data['admin_profile'] = {
            'can_approve_issuers': admin.can_approve_issuers,
            'can_revoke_issuers': admin.can_revoke_issuers,
            'can_view_analytics': admin.can_view_analytics,
            'can_resolve_flags': admin.can_resolve_flags,
        }

    return Response(data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    request_body=UpdateProfileSerializer,
    responses={200: 'Profile updated successfully'}
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update current user profile.
    PUT /api/auth/profile/
    JWT required.
    """
    user = request.user
    serializer = UpdateProfileSerializer(
        user,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                'message': 'Profile updated successfully.',
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=ChangePasswordSerializer,
    responses={200: 'Password changed successfully'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password.
    POST /api/auth/change-password/
    JWT required.
    """
    user = request.user
    serializer = ChangePasswordSerializer(data=request.data)

    if serializer.is_valid():
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Old password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(
            {'message': 'Password changed successfully. Please login again.'},
            status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_token(request):
    """
    Verify a JWT token is valid and return user info.
    GET /api/auth/verify/
    JWT required.
    """
    user = request.user
    return Response(
        {
            'valid': True,
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'is_verified': user.is_verified,
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """
    List all users.
    GET /api/auth/users/
    Admin only.
    """
    if request.user.role != User.Role.ADMIN:
        return Response(
            {'error': 'Only administrators can view all users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    responses={200: 'User deactivated successfully'}
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def deactivate_user(request, user_id):
    """
    Deactivate a user account.
    PUT /api/auth/users/{user_id}/deactivate/
    Admin only.
    """
    if request.user.role != User.Role.ADMIN:
        return Response(
            {'error': 'Only administrators can deactivate users.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    user.is_active = False
    user.save()

    return Response(
        {'message': f'User {user.email} deactivated successfully.'},
        status=status.HTTP_200_OK
    )
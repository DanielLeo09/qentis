import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from auth_app.models import User, Issuer, Verifier, Administrator
from auth_app.views import get_tokens_for_user


class TestUserModel(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )
        Issuer.objects.create(user=self.user)

    def test_user_created_successfully(self):
        self.assertIsNotNone(self.user.id)
        self.assertEqual(self.user.email, 'test@example.com')

    def test_user_default_role_is_verifier(self):
        user = User.objects.create_user(
            email='verifier@example.com',
            password='TestPass123!',
        )
        self.assertEqual(user.role, User.Role.VERIFIER)

    def test_user_str_representation(self):
        self.assertEqual(str(self.user), 'test@example.com (ISSUER)')

    def test_issuer_profile_linked_to_user(self):
        self.assertTrue(hasattr(self.user, 'issuer_profile'))

    def test_verifier_profile_linked_to_user(self):
        user = User.objects.create_user(
            email='verifier2@example.com',
            password='TestPass123!',
            role=User.Role.VERIFIER,
        )
        Verifier.objects.create(user=user)
        self.assertTrue(hasattr(user, 'verifier_profile'))

    def test_admin_profile_linked_to_user(self):
        user = User.objects.create_user(
            email='admin@example.com',
            password='TestPass123!',
            role=User.Role.ADMIN,
        )
        Administrator.objects.create(user=user)
        self.assertTrue(hasattr(user, 'admin_profile'))

    def test_password_is_hashed(self):
        self.assertNotEqual(self.user.password, 'TestPass123!')
        self.assertTrue(self.user.check_password('TestPass123!'))

    def test_user_is_active_by_default(self):
        self.assertTrue(self.user.is_active)

    def test_user_is_not_verified_by_default(self):
        self.assertFalse(self.user.is_verified)


class TestRegisterEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.valid_data = {
            'email': 'newuser@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'role': 'ISSUER',
        }

    def test_register_issuer_succeeds(self):
        response = self.client.post('/api/auth/register/', data=self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'ISSUER')

    def test_register_verifier_succeeds(self):
        data = self.valid_data.copy()
        data['email'] = 'verifier@example.com'
        data['role'] = 'VERIFIER'
        response = self.client.post('/api/auth/register/', data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['role'], 'VERIFIER')

    def test_register_returns_access_and_refresh_tokens(self):
        response = self.client.post('/api/auth/register/', data=self.valid_data, format='json')
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

    def test_register_fails_with_duplicate_email(self):
        self.client.post('/api/auth/register/', data=self.valid_data, format='json')
        response = self.client.post('/api/auth/register/', data=self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_fails_with_mismatched_passwords(self):
        data = self.valid_data.copy()
        data['password_confirm'] = 'DifferentPass!'
        response = self.client.post('/api/auth/register/', data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_fails_with_missing_email(self):
        data = self.valid_data.copy()
        del data['email']
        response = self.client.post('/api/auth/register/', data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_fails_with_invalid_email(self):
        data = self.valid_data.copy()
        data['email'] = 'not-an-email'
        response = self.client.post('/api/auth/register/', data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_creates_issuer_profile(self):
        self.client.post('/api/auth/register/', data=self.valid_data, format='json')
        user = User.objects.get(email='newuser@example.com')
        self.assertTrue(hasattr(user, 'issuer_profile'))

    def test_register_normalises_email_to_lowercase(self):
        data = self.valid_data.copy()
        data['email'] = 'UPPERCASE@EXAMPLE.COM'
        self.client.post('/api/auth/register/', data=data, format='json')
        self.assertTrue(User.objects.filter(email='uppercase@example.com').exists())


class TestLoginEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='login@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )

    def test_login_succeeds_with_valid_credentials(self):
        response = self.client.post('/api/auth/login/', data={
            'email': 'login@example.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

    def test_login_returns_user_data(self):
        response = self.client.post('/api/auth/login/', data={
            'email': 'login@example.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.data['user']['email'], 'login@example.com')
        self.assertEqual(response.data['user']['role'], 'ISSUER')

    def test_login_fails_with_wrong_password(self):
        response = self.client.post('/api/auth/login/', data={
            'email': 'login@example.com',
            'password': 'WrongPassword!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_fails_with_nonexistent_email(self):
        response = self.client.post('/api/auth/login/', data={
            'email': 'nobody@example.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_fails_with_missing_credentials(self):
        response = self.client.post('/api/auth/login/', data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_fails_for_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post('/api/auth/login/', data={
            'email': 'login@example.com',
            'password': 'TestPass123!',
        }, format='json')
        # Django's ModelBackend returns None for inactive users, so the view
        # hits the "Invalid credentials" branch (401) rather than the
        # explicit is_active check (403).
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])


class TestLogoutEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='logout@example.com',
            password='TestPass123!',
        )
        self.tokens = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens["access"]}')

    def test_logout_succeeds_with_valid_refresh_token(self):
        response = self.client.post('/api/auth/logout/', data={
            'refresh_token': self.tokens['refresh'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_fails_without_refresh_token(self):
        response = self.client.post('/api/auth/logout/', data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self):
        client = APIClient()
        response = client.post('/api/auth/logout/', data={
            'refresh_token': self.tokens['refresh'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_with_invalid_token_returns_400(self):
        response = self.client.post('/api/auth/logout/', data={
            'refresh_token': 'invalid-refresh-token',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestTokenRefreshEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='refresh@example.com',
            password='TestPass123!',
        )
        self.tokens = get_tokens_for_user(self.user)

    def test_refresh_returns_new_access_token(self):
        response = self.client.post('/api/auth/token/refresh/', data={
            'refresh_token': self.tokens['refresh'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_fails_with_invalid_token(self):
        response = self.client.post('/api/auth/token/refresh/', data={
            'refresh_token': 'bad-token',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_fails_without_token(self):
        response = self.client.post('/api/auth/token/refresh/', data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestProfileEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.issuer = User.objects.create_user(
            email='issuer@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )
        Issuer.objects.create(
            user=self.issuer,
            institution_name='Test University',
            institution_type='UNIVERSITY',
        )
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='TestPass123!',
            role=User.Role.ADMIN,
        )
        Administrator.objects.create(user=self.admin)
        tokens = get_tokens_for_user(self.issuer)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def test_profile_returns_user_data(self):
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'issuer@example.com')

    def test_profile_includes_issuer_profile_for_issuer(self):
        response = self.client.get('/api/auth/profile/')
        self.assertIn('issuer_profile', response.data)
        self.assertEqual(response.data['issuer_profile']['institution_name'], 'Test University')

    def test_profile_includes_admin_profile_for_admin(self):
        tokens = get_tokens_for_user(self.admin)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('admin_profile', response.data)
        self.assertIn('can_approve_issuers', response.data['admin_profile'])

    def test_profile_requires_authentication(self):
        client = APIClient()
        response = client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestUpdateProfileEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='update@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )
        Issuer.objects.create(user=self.user)
        tokens = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def test_update_email_succeeds(self):
        response = self.client.put('/api/auth/profile/update/', data={
            'email': 'updated@example.com',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')

    def test_update_issuer_profile_succeeds(self):
        response = self.client.put('/api/auth/profile/update/', data={
            'issuer_profile': {
                'institution_name': 'New University',
                'country': 'Cameroon',
                'city': 'Douala',
            },
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.issuer_profile.refresh_from_db()
        self.assertEqual(self.user.issuer_profile.institution_name, 'New University')

    def test_update_requires_authentication(self):
        client = APIClient()
        response = client.put('/api/auth/profile/update/', data={'email': 'x@x.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestChangePasswordEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='chpass@example.com',
            password='OldPass123!',
        )
        tokens = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def test_change_password_succeeds(self):
        response = self.client.post('/api/auth/change-password/', data={
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'NewPass456!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

    def test_change_password_fails_with_wrong_old_password(self):
        response = self.client.post('/api/auth/change-password/', data={
            'old_password': 'WrongOldPass!',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'NewPass456!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_fails_with_mismatched_new_passwords(self):
        response = self.client.post('/api/auth/change-password/', data={
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'DifferentPass!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_requires_authentication(self):
        client = APIClient()
        response = client.post('/api/auth/change-password/', data={
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'NewPass456!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestVerifyTokenEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='verify@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )
        tokens = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def test_verify_returns_valid_true(self):
        response = self.client.get('/api/auth/verify/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['email'], 'verify@example.com')
        self.assertEqual(response.data['role'], 'ISSUER')

    def test_verify_includes_user_id(self):
        response = self.client.get('/api/auth/verify/')
        self.assertEqual(response.data['user_id'], str(self.user.id))

    def test_verify_requires_authentication(self):
        client = APIClient()
        response = client.get('/api/auth/verify/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestListUsersEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='TestPass123!',
            role=User.Role.ADMIN,
        )
        self.issuer = User.objects.create_user(
            email='issuer@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )
        tokens = get_tokens_for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def test_admin_can_list_users(self):
        response = self.client.get('/api/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_non_admin_cannot_list_users(self):
        tokens = get_tokens_for_user(self.issuer)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = client.get('/api/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_users_requires_authentication(self):
        client = APIClient()
        response = client.get('/api/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestDeactivateUserEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='TestPass123!',
            role=User.Role.ADMIN,
        )
        self.target_user = User.objects.create_user(
            email='target@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )
        tokens = get_tokens_for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def test_admin_can_deactivate_user(self):
        response = self.client.put(f'/api/auth/users/{self.target_user.id}/deactivate/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)

    def test_non_admin_cannot_deactivate(self):
        user = User.objects.create_user(
            email='regular@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )
        tokens = get_tokens_for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = client.put(f'/api/auth/users/{self.target_user.id}/deactivate/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deactivate_nonexistent_user_returns_404(self):
        response = self.client.put(f'/api/auth/users/{uuid.uuid4()}/deactivate/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deactivate_requires_authentication(self):
        client = APIClient()
        response = client.put(f'/api/auth/users/{self.target_user.id}/deactivate/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Additional tests for ≥80% coverage
# ---------------------------------------------------------------------------

from unittest.mock import patch


class TestUserManagerExtended(TestCase):

    def test_create_user_without_email_raises_value_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='Test123!')

    def test_create_superuser_sets_staff_superuser_admin_verified(self):
        superuser = User.objects.create_superuser(
            email='super@example.com',
            password='SuperPass123!'
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertEqual(superuser.role, User.Role.ADMIN)
        self.assertTrue(superuser.is_verified)


class TestModelStrRepresentations(TestCase):

    def test_issuer_str_representation(self):
        user = User.objects.create_user(email='issuer@str.com', password='Pass123!')
        issuer = Issuer.objects.create(user=user, institution_name='ICT University')
        self.assertIn('ICT University', str(issuer))
        self.assertIn('issuer@str.com', str(issuer))

    def test_verifier_str_representation(self):
        user = User.objects.create_user(email='verifier@str.com', password='Pass123!')
        verifier = Verifier.objects.create(user=user)
        self.assertIn('verifier@str.com', str(verifier))

    def test_administrator_str_representation(self):
        user = User.objects.create_user(email='admin@str.com', password='Pass123!')
        admin = Administrator.objects.create(user=user)
        self.assertIn('admin@str.com', str(admin))


class TestRegisterAdminRole(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_register_admin_role_creates_admin_profile(self):
        response = self.client.post('/api/auth/register/', data={
            'email': 'newadmin@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'role': 'ADMIN',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='newadmin@example.com')
        self.assertTrue(hasattr(user, 'admin_profile'))

    def test_register_admin_returns_tokens(self):
        response = self.client.post('/api/auth/register/', data={
            'email': 'admintoken@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'role': 'ADMIN',
        }, format='json')
        self.assertIn('access', response.data['tokens'])


class TestLoginIsActiveBranch(TestCase):

    def test_login_returns_403_when_authenticate_returns_inactive_user(self):
        user = User.objects.create_user(
            email='inactive_mock@example.com',
            password='TestPass123!',
            is_active=False,
        )
        client = APIClient()
        with patch('auth_app.views.authenticate', return_value=user):
            response = client.post('/api/auth/login/', data={
                'email': 'inactive_mock@example.com',
                'password': 'TestPass123!',
            }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestProfileForVerifier(TestCase):

    def test_verifier_profile_has_no_extra_role_data(self):
        user = User.objects.create_user(
            email='verifier_extra@example.com',
            password='TestPass123!',
            role=User.Role.VERIFIER,
        )
        Verifier.objects.create(user=user)
        tokens = get_tokens_for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('issuer_profile', response.data)
        self.assertNotIn('admin_profile', response.data)

    def test_profile_returns_is_active_and_is_verified(self):
        user = User.objects.create_user(
            email='fields_check@example.com',
            password='TestPass123!',
            role=User.Role.VERIFIER,
        )
        tokens = get_tokens_for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = client.get('/api/auth/profile/')
        self.assertIn('is_active', response.data)
        self.assertIn('is_verified', response.data)


class TestUpdateProfileInvalidData(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='invalid_update@example.com',
            password='TestPass123!',
            role=User.Role.ISSUER,
        )
        Issuer.objects.create(user=self.user)
        tokens = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def test_update_profile_with_invalid_email_returns_400(self):
        response = self.client.put('/api/auth/profile/update/', data={
            'email': 'not-a-valid-email',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_profile_with_duplicate_email_returns_400(self):
        User.objects.create_user(email='taken@example.com', password='Pass123!')
        response = self.client.put('/api/auth/profile/update/', data={
            'email': 'taken@example.com',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestVerifyTokenFields(TestCase):

    def test_verify_token_returns_is_active_and_is_verified(self):
        user = User.objects.create_user(
            email='verify_fields@example.com',
            password='TestPass123!',
            role=User.Role.ADMIN,
        )
        tokens = get_tokens_for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = client.get('/api/auth/verify/')
        self.assertIn('is_active', response.data)
        self.assertIn('is_verified', response.data)
        self.assertEqual(response.data['role'], 'ADMIN')

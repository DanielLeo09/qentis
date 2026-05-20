import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from item_app.models import (
    Item, CertificateDetail, PharmaceuticalDetail, DocumentDetail, BanknoteDetail
)


class MockUser:
    """Minimal user object for bypassing JWT in item-registration tests.
    The service checks HTTP_X_USER_ID / HTTP_X_USER_ROLE headers for
    authorization, not request.user, so any authenticated object works."""
    is_authenticated = True

    def __init__(self):
        self.id = uuid.uuid4()


class TestItemModel(TestCase):

    def setUp(self):
        self.issuer_id = uuid.uuid4()
        self.institution_id = uuid.uuid4()
        self.item = Item.objects.create(
            issuer_id=self.issuer_id,
            institution_id=self.institution_id,
            category=Item.Category.CERTIFICATE,
            status=Item.Status.REGISTERED,
        )

    def test_item_created_successfully(self):
        self.assertIsNotNone(self.item.id)
        self.assertEqual(self.item.category, Item.Category.CERTIFICATE)

    def test_item_default_status_is_registered(self):
        self.assertEqual(self.item.status, Item.Status.REGISTERED)

    def test_item_str_representation(self):
        self.assertIn('CERTIFICATE', str(self.item))

    def test_certificate_detail_cascade_delete(self):
        CertificateDetail.objects.create(
            item=self.item,
            student_name='John Doe',
            matricule='MAT001',
            degree='BSc Computer Science',
            institution_name='ICT University',
            graduation_date='2024-06-15',
            grade='First Class',
        )
        self.assertEqual(CertificateDetail.objects.filter(item=self.item).count(), 1)
        self.item.delete()
        self.assertEqual(CertificateDetail.objects.count(), 0)

    def test_certificate_get_hash_fields(self):
        detail = CertificateDetail.objects.create(
            item=self.item,
            student_name='John Doe',
            matricule='MAT001',
            degree='BSc',
            institution_name='ICT University',
            graduation_date='2024-06-15',
            grade='First Class',
        )
        hash_fields = detail.get_hash_fields()
        self.assertIn('John Doe', hash_fields)
        self.assertIn('MAT001', hash_fields)
        self.assertIn('ICT University', hash_fields)

    def test_pharmaceutical_get_hash_fields(self):
        item = Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.PHARMACEUTICAL,
        )
        detail = PharmaceuticalDetail.objects.create(
            item=item,
            drug_name='Paracetamol',
            batch_number='BATCH001',
            manufacturer='PharmaLab',
            production_date='2024-01-01',
            expiry_date='2026-01-01',
            factory_location='Yaounde',
        )
        hash_fields = detail.get_hash_fields()
        self.assertIn('Paracetamol', hash_fields)
        self.assertIn('BATCH001', hash_fields)

    def test_document_get_hash_fields(self):
        item = Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.DOCUMENT,
        )
        detail = DocumentDetail.objects.create(
            item=item,
            document_type='Passport',
            owner_name='Jane Smith',
            issuing_authority='Ministry',
            reference_number='REF001',
            location='Yaounde',
            issue_date='2024-01-15',
        )
        hash_fields = detail.get_hash_fields()
        self.assertIn('Jane Smith', hash_fields)
        self.assertIn('REF001', hash_fields)

    def test_banknote_get_hash_fields(self):
        item = Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.BANKNOTE,
        )
        detail = BanknoteDetail.objects.create(
            item=item,
            currency='XAF',
            denomination='5000.00',
            serial_number='BN001',
            series='2024',
            issue_date='2024-01-01',
            issuing_bank='BEAC',
        )
        hash_fields = detail.get_hash_fields()
        self.assertIn('XAF', hash_fields)
        self.assertIn('BN001', hash_fields)


class TestRegisterItemEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.issuer_id = str(uuid.uuid4())
        self.institution_id = str(uuid.uuid4())
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(
            HTTP_X_USER_ID=self.issuer_id,
            HTTP_X_USER_ROLE='ISSUER',
        )
        self.certificate_data = {
            'category': 'CERTIFICATE',
            'institution_id': self.institution_id,
            'student_name': 'John Doe',
            'matricule': 'MAT001',
            'degree': 'BSc Computer Science',
            'institution_name': 'ICT University',
            'graduation_date': '2024-06-15',
            'grade': 'First Class',
        }

    def test_issuer_can_register_certificate(self):
        response = self.client.post('/api/items/register/', data=self.certificate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['item']['category'], 'CERTIFICATE')
        self.assertEqual(response.data['item']['status'], 'REGISTERED')

    def test_register_creates_certificate_detail(self):
        response = self.client.post('/api/items/register/', data=self.certificate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item_id = response.data['item']['id']
        self.assertTrue(CertificateDetail.objects.filter(item_id=item_id).exists())

    def test_register_pharmaceutical(self):
        response = self.client.post('/api/items/register/', data={
            'category': 'PHARMACEUTICAL',
            'institution_id': self.institution_id,
            'drug_name': 'Paracetamol 500mg',
            'batch_number': 'BATCH001',
            'manufacturer': 'PharmaLab',
            'production_date': '2024-01-01',
            'expiry_date': '2026-01-01',
            'factory_location': 'Yaounde, Cameroon',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['item']['category'], 'PHARMACEUTICAL')

    def test_register_document(self):
        response = self.client.post('/api/items/register/', data={
            'category': 'DOCUMENT',
            'institution_id': self.institution_id,
            'document_type': 'Passport',
            'owner_name': 'Jane Smith',
            'issuing_authority': 'Ministry of External Relations',
            'reference_number': 'REF001',
            'location': 'Yaounde',
            'issue_date': '2024-01-15',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['item']['category'], 'DOCUMENT')

    def test_register_banknote(self):
        response = self.client.post('/api/items/register/', data={
            'category': 'BANKNOTE',
            'institution_id': self.institution_id,
            'currency': 'XAF',
            'denomination': '5000.00',
            'serial_number': 'BN001',
            'series': '2024',
            'issue_date': '2024-01-01',
            'issuing_bank': 'BEAC',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['item']['category'], 'BANKNOTE')

    def test_register_fails_without_user_id(self):
        client = APIClient()
        client.force_authenticate(user=MockUser())
        response = client.post('/api/items/register/', data=self.certificate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_fails_for_non_issuer(self):
        client = APIClient()
        client.force_authenticate(user=MockUser())
        client.credentials(
            HTTP_X_USER_ID=self.issuer_id,
            HTTP_X_USER_ROLE='VERIFIER',
        )
        response = client.post('/api/items/register/', data=self.certificate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_register_fails_with_missing_required_fields(self):
        response = self.client.post('/api/items/register/', data={
            'category': 'CERTIFICATE',
            'student_name': 'John Doe',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_item_has_blockchain_hash(self):
        response = self.client.post('/api/items/register/', data=self.certificate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['item']['blockchain_hash'])

    def test_register_item_has_serial_number(self):
        response = self.client.post('/api/items/register/', data=self.certificate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['item']['serial_number'])

    def test_register_item_has_qr_code_url(self):
        response = self.client.post('/api/items/register/', data=self.certificate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['item']['qr_code_url'])


class TestMyItemsEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.issuer_id = str(uuid.uuid4())
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(
            HTTP_X_USER_ID=self.issuer_id,
            HTTP_X_USER_ROLE='ISSUER',
        )
        Item.objects.create(
            issuer_id=uuid.UUID(self.issuer_id),
            institution_id=uuid.uuid4(),
            category=Item.Category.CERTIFICATE,
        )

    def test_issuer_can_view_own_items(self):
        response = self.client.get('/api/items/my-items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_returns_empty_list_for_issuer_with_no_items(self):
        new_id = str(uuid.uuid4())
        client = APIClient()
        client.force_authenticate(user=MockUser())
        client.credentials(HTTP_X_USER_ID=new_id)
        response = client.get('/api/items/my-items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_fails_without_user_id_header(self):
        client = APIClient()
        client.force_authenticate(user=MockUser())
        response = client.get('/api/items/my-items/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_returns_own_items(self):
        other_issuer_id = str(uuid.uuid4())
        Item.objects.create(
            issuer_id=uuid.UUID(other_issuer_id),
            institution_id=uuid.uuid4(),
            category=Item.Category.PHARMACEUTICAL,
        )
        response = self.client.get('/api/items/my-items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class TestItemDetailEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.issuer_id = str(uuid.uuid4())
        self.client.force_authenticate(user=MockUser())
        self.item = Item.objects.create(
            issuer_id=uuid.UUID(self.issuer_id),
            institution_id=uuid.uuid4(),
            category=Item.Category.CERTIFICATE,
        )

    def test_issuer_can_view_own_item(self):
        self.client.credentials(
            HTTP_X_USER_ID=self.issuer_id,
            HTTP_X_USER_ROLE='ISSUER',
        )
        response = self.client.get(f'/api/items/{self.item.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['id']), str(self.item.id))

    def test_admin_can_view_any_item(self):
        admin_id = str(uuid.uuid4())
        self.client.credentials(
            HTTP_X_USER_ID=admin_id,
            HTTP_X_USER_ROLE='ADMIN',
        )
        response = self.client.get(f'/api/items/{self.item.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_issuer_cannot_view_item(self):
        other_issuer_id = str(uuid.uuid4())
        self.client.credentials(
            HTTP_X_USER_ID=other_issuer_id,
            HTTP_X_USER_ROLE='ISSUER',
        )
        response = self.client.get(f'/api/items/{self.item.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_item_returns_404(self):
        self.client.credentials(
            HTTP_X_USER_ID=self.issuer_id,
            HTTP_X_USER_ROLE='ISSUER',
        )
        response = self.client.get(f'/api/items/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestRevokeItemEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.issuer_id = str(uuid.uuid4())
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(
            HTTP_X_USER_ID=self.issuer_id,
            HTTP_X_USER_ROLE='ISSUER',
        )
        self.item = Item.objects.create(
            issuer_id=uuid.UUID(self.issuer_id),
            institution_id=uuid.uuid4(),
            category=Item.Category.CERTIFICATE,
            status=Item.Status.REGISTERED,
        )

    def test_issuer_can_revoke_own_item(self):
        response = self.client.put(f'/api/items/{self.item.id}/revoke/', data={
            'reason': 'Certificate was issued in error and must be cancelled.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.Status.REVOKED)

    def test_revoke_sets_revoked_at_timestamp(self):
        self.client.put(f'/api/items/{self.item.id}/revoke/', data={
            'reason': 'Certificate was issued in error and must be cancelled.',
        }, format='json')
        self.item.refresh_from_db()
        self.assertIsNotNone(self.item.revoked_at)

    def test_revoke_fails_with_short_reason(self):
        response = self.client.put(f'/api/items/{self.item.id}/revoke/', data={
            'reason': 'Short',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revoke_fails_without_reason(self):
        response = self.client.put(f'/api/items/{self.item.id}/revoke/', data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_revoke_already_revoked_item(self):
        self.item.status = Item.Status.REVOKED
        self.item.save()
        response = self.client.put(f'/api/items/{self.item.id}/revoke/', data={
            'reason': 'Trying to revoke again should fail here.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_issuer_cannot_revoke_item(self):
        other_client = APIClient()
        other_client.force_authenticate(user=MockUser())
        other_client.credentials(
            HTTP_X_USER_ID=str(uuid.uuid4()),
            HTTP_X_USER_ROLE='ISSUER',
        )
        response = other_client.put(f'/api/items/{self.item.id}/revoke/', data={
            'reason': 'Trying to revoke someone elses item.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoke_nonexistent_item_returns_404(self):
        response = self.client.put(f'/api/items/{uuid.uuid4()}/revoke/', data={
            'reason': 'This item does not exist in the database.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestAllItemsEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.CERTIFICATE,
        )
        Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.PHARMACEUTICAL,
        )
        revoked_item = Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.CERTIFICATE,
        )
        revoked_item.status = Item.Status.REVOKED
        revoked_item.save()

    def test_admin_can_view_all_items(self):
        self.client.credentials(HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/items/all/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_non_admin_cannot_view_all_items(self):
        self.client.credentials(HTTP_X_USER_ROLE='ISSUER')
        response = self.client.get('/api/items/all/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_role_header_returns_403(self):
        response = self.client.get('/api/items/all/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_filter_by_category(self):
        self.client.credentials(HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/items/all/?category=PHARMACEUTICAL')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['category'], 'PHARMACEUTICAL')

    def test_admin_can_filter_by_status(self):
        self.client.credentials(HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/items/all/?status=REVOKED')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'REVOKED')

    def test_admin_can_filter_by_category_and_status(self):
        self.client.credentials(HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/items/all/?category=CERTIFICATE&status=REGISTERED')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


# ---------------------------------------------------------------------------
# Additional tests for ≥80% coverage
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
from item_app.views import generate_hash, call_blockchain_service, call_output_service


class TestDetailStrRepresentations(TestCase):

    def setUp(self):
        self.issuer_id = uuid.uuid4()
        self.institution_id = uuid.uuid4()

    def _make_item(self, category):
        return Item.objects.create(
            issuer_id=self.issuer_id,
            institution_id=self.institution_id,
            category=category,
        )

    def test_certificate_detail_str(self):
        item = self._make_item(Item.Category.CERTIFICATE)
        detail = CertificateDetail.objects.create(
            item=item, student_name='Alice Smith', matricule='M001',
            degree='BSc CS', institution_name='ICT', graduation_date='2024-06-01', grade='First',
        )
        self.assertIn('Alice Smith', str(detail))
        self.assertIn('BSc CS', str(detail))

    def test_pharmaceutical_detail_str(self):
        item = self._make_item(Item.Category.PHARMACEUTICAL)
        detail = PharmaceuticalDetail.objects.create(
            item=item, drug_name='Aspirin', batch_number='B001',
            manufacturer='Lab', production_date='2024-01-01',
            expiry_date='2026-01-01', factory_location='Douala',
        )
        self.assertIn('Aspirin', str(detail))
        self.assertIn('B001', str(detail))

    def test_document_detail_str(self):
        item = self._make_item(Item.Category.DOCUMENT)
        detail = DocumentDetail.objects.create(
            item=item, document_type='Passport', owner_name='Bob Jones',
            issuing_authority='Ministry', reference_number='R001',
            location='Yaounde', issue_date='2024-01-01',
        )
        self.assertIn('Passport', str(detail))
        self.assertIn('Bob Jones', str(detail))

    def test_banknote_detail_str(self):
        item = self._make_item(Item.Category.BANKNOTE)
        detail = BanknoteDetail.objects.create(
            item=item, currency='XAF', denomination='5000.00',
            serial_number='BN999', series='2024',
            issue_date='2024-01-01', issuing_bank='BEAC',
        )
        self.assertIn('XAF', str(detail))
        self.assertIn('BN999', str(detail))


class TestViewHelperFunctions(TestCase):

    def test_generate_hash_returns_64_char_hex(self):
        h = generate_hash('some field data here')
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in h))

    def test_generate_hash_is_deterministic(self):
        self.assertEqual(generate_hash('abc'), generate_hash('abc'))

    def test_generate_hash_differs_for_different_inputs(self):
        self.assertNotEqual(generate_hash('abc'), generate_hash('xyz'))

    def test_call_blockchain_service_returns_mock_on_connection_failure(self):
        item_id = uuid.uuid4()
        result = call_blockchain_service(item_id, 'CERTIFICATE', 'fields')
        self.assertIn('hash', result)
        self.assertIn('transaction_hash', result)
        self.assertIn('mock-tx', result['transaction_hash'])

    def test_call_blockchain_service_success_path_returns_tx_hash(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {'tx_hash': '0xdeadbeef123'}
        with patch('item_app.views.requests.post', return_value=mock_resp):
            result = call_blockchain_service(
                uuid.uuid4(), 'CERTIFICATE', 'fields',
                issuer_id='user-123', issuer_name='Test University',
            )
        self.assertEqual(result['transaction_hash'], '0xdeadbeef123')

    def test_call_blockchain_service_uses_provided_issuer_info(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {'tx_hash': '0xabc'}
        with patch('item_app.views.requests.post', return_value=mock_resp) as mock_post:
            call_blockchain_service(
                uuid.uuid4(), 'PHARMACEUTICAL', 'fields',
                issuer_id='issuer-abc', issuer_name='PharmaLab',
            )
        call_kwargs = mock_post.call_args[1]['json']
        self.assertEqual(call_kwargs['issuer_name'], 'PharmaLab')

    def test_call_output_service_returns_mock_on_connection_failure(self):
        item_id = uuid.uuid4()
        result = call_output_service(item_id, 'CERTIFICATE')
        self.assertIn('qr_code_url', result)
        self.assertIn('serial_number', result)

    def test_call_output_service_success_path_returns_service_data(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            'qr_code_url': 'http://example.com/qr.png',
            'serial_number': 'QNT-2024-CERT-TEST01',
        }
        with patch('item_app.views.requests.post', return_value=mock_resp):
            result = call_output_service(uuid.uuid4(), 'CERTIFICATE')
        self.assertEqual(result['serial_number'], 'QNT-2024-CERT-TEST01')
        self.assertEqual(result['qr_code_url'], 'http://example.com/qr.png')


class TestRevokeItemMissingHeader(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=MockUser())
        self.item = Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.CERTIFICATE,
        )

    def test_revoke_fails_without_user_id_header(self):
        response = self.client.put(f'/api/items/{self.item.id}/revoke/', data={
            'reason': 'Testing missing user id header scenario here.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestItemModelAdditional(TestCase):

    def test_item_str_contains_category(self):
        item = Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.PHARMACEUTICAL,
        )
        self.assertIn('PHARMACEUTICAL', str(item))

    def test_item_has_registered_at_timestamp(self):
        item = Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.DOCUMENT,
        )
        self.assertIsNotNone(item.registered_at)

    def test_item_revoked_at_is_none_by_default(self):
        item = Item.objects.create(
            issuer_id=uuid.uuid4(),
            institution_id=uuid.uuid4(),
            category=Item.Category.BANKNOTE,
        )
        self.assertIsNone(item.revoked_at)

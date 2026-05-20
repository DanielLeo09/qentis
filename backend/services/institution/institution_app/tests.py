import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from institution_app.models import Institution, InstitutionDocument


class MockUser:
    """Minimal user for bypassing JWT. The institution service reads role and
    user identity from HTTP_X_USER_ID / HTTP_X_USER_ROLE headers, not from
    request.user, so any object with is_authenticated=True works."""
    is_authenticated = True

    def __init__(self):
        self.id = uuid.uuid4()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestInstitutionModel(TestCase):

    def setUp(self):
        self.user_id = uuid.uuid4()
        self.institution = Institution.objects.create(
            user_id=self.user_id,
            name='ICT University Cameroon',
            institution_type=Institution.InstitutionType.UNIVERSITY,
            country='Cameroon',
            city='Yaounde',
            contact_email='admin@ict.cm',
            status=Institution.Status.PENDING,
        )

    def test_institution_created_successfully(self):
        self.assertIsNotNone(self.institution.id)
        self.assertEqual(self.institution.name, 'ICT University Cameroon')

    def test_institution_default_status_is_pending(self):
        self.assertEqual(self.institution.status, Institution.Status.PENDING)

    def test_institution_str_representation(self):
        self.assertEqual(str(self.institution), 'ICT University Cameroon (PENDING)')

    def test_institution_approval(self):
        self.institution.status = Institution.Status.APPROVED
        self.institution.save()
        updated = Institution.objects.get(id=self.institution.id)
        self.assertEqual(updated.status, Institution.Status.APPROVED)

    def test_institution_rejection_with_reason(self):
        self.institution.status = Institution.Status.REJECTED
        self.institution.rejection_reason = 'Documents not valid'
        self.institution.save()
        updated = Institution.objects.get(id=self.institution.id)
        self.assertEqual(updated.status, Institution.Status.REJECTED)
        self.assertEqual(updated.rejection_reason, 'Documents not valid')

    def test_institution_revocation(self):
        self.institution.status = Institution.Status.REVOKED
        self.institution.save()
        updated = Institution.objects.get(id=self.institution.id)
        self.assertEqual(updated.status, Institution.Status.REVOKED)

    def test_document_cascade_delete(self):
        InstitutionDocument.objects.create(
            institution=self.institution,
            document_type=InstitutionDocument.DocumentType.LICENSE,
        )
        self.assertEqual(
            InstitutionDocument.objects.filter(institution=self.institution).count(), 1
        )
        self.institution.delete()
        self.assertEqual(InstitutionDocument.objects.count(), 0)

    def test_institution_has_created_at_timestamp(self):
        self.assertIsNotNone(self.institution.created_at)

    def test_institution_approved_by_is_none_by_default(self):
        self.assertIsNone(self.institution.approved_by)


class TestInstitutionDocumentModel(TestCase):

    def setUp(self):
        self.institution = Institution.objects.create(
            user_id=uuid.uuid4(),
            name='Doc Test University',
            institution_type=Institution.InstitutionType.UNIVERSITY,
            country='Cameroon',
            city='Yaounde',
            contact_email='doc@test.cm',
        )

    def test_document_str_representation(self):
        doc = InstitutionDocument.objects.create(
            institution=self.institution,
            document_type=InstitutionDocument.DocumentType.LICENSE,
        )
        self.assertIn('Doc Test University', str(doc))
        self.assertIn('LICENSE', str(doc))

    def test_document_default_type_is_other(self):
        doc = InstitutionDocument.objects.create(institution=self.institution)
        self.assertEqual(doc.document_type, InstitutionDocument.DocumentType.OTHER)


# ---------------------------------------------------------------------------
# Apply endpoint
# ---------------------------------------------------------------------------

class TestApplyEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user_id = str(uuid.uuid4())
        self.valid_data = {
            'name': 'ICT University Cameroon',
            'institution_type': 'UNIVERSITY',
            'country': 'Cameroon',
            'city': 'Yaounde',
            'contact_email': 'admin@ict.cm',
        }

    def test_apply_succeeds_with_valid_data(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.user_id, HTTP_X_USER_ROLE='ISSUER')
        response = self.client.post('/api/institution/apply/', data=self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'PENDING')

    def test_apply_returns_application_id(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.user_id, HTTP_X_USER_ROLE='ISSUER')
        response = self.client.post('/api/institution/apply/', data=self.valid_data, format='json')
        self.assertIn('application_id', response.data)

    def test_apply_fails_without_user_id(self):
        self.client.force_authenticate(user=MockUser())
        response = self.client.post('/api/institution/apply/', data=self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_requires_authentication(self):
        response = self.client.post('/api/institution/apply/', data=self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_apply_fails_with_missing_fields(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.user_id, HTTP_X_USER_ROLE='ISSUER')
        response = self.client.post('/api/institution/apply/', data={'name': 'ICT University'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_fails_with_duplicate_application(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.user_id, HTTP_X_USER_ROLE='ISSUER')
        self.client.post('/api/institution/apply/', data=self.valid_data, format='json')
        response = self.client.post('/api/institution/apply/', data=self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_fails_with_invalid_email(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.user_id, HTTP_X_USER_ROLE='ISSUER')
        data = self.valid_data.copy()
        data['contact_email'] = 'not-an-email'
        response = self.client.post('/api/institution/apply/', data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_normalises_email_to_lowercase(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.user_id, HTTP_X_USER_ROLE='ISSUER')
        data = self.valid_data.copy()
        data['contact_email'] = 'ADMIN@ICT.CM'
        self.client.post('/api/institution/apply/', data=data, format='json')
        self.assertTrue(Institution.objects.filter(contact_email='admin@ict.cm').exists())

    def test_apply_fails_with_short_name(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.user_id, HTTP_X_USER_ROLE='ISSUER')
        data = self.valid_data.copy()
        data['name'] = 'AB'
        response = self.client.post('/api/institution/apply/', data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_all_institution_types_accepted(self):
        for itype in ['UNIVERSITY', 'HOSPITAL', 'NOTARY', 'BANK', 'MANUFACTURER']:
            uid = str(uuid.uuid4())
            self.client.force_authenticate(user=MockUser())
            self.client.credentials(HTTP_X_USER_ID=uid, HTTP_X_USER_ROLE='ISSUER')
            data = self.valid_data.copy()
            data['institution_type'] = itype
            data['contact_email'] = f'{itype.lower()}@test.cm'
            response = self.client.post('/api/institution/apply/', data=data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Application status endpoint
# ---------------------------------------------------------------------------

class TestApplicationStatusEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user_id = str(uuid.uuid4())
        Institution.objects.create(
            user_id=uuid.UUID(self.user_id),
            name='Test University',
            institution_type=Institution.InstitutionType.UNIVERSITY,
            country='Cameroon',
            city='Yaounde',
            contact_email='test@university.cm',
            status=Institution.Status.PENDING,
        )

    def test_status_returns_institution_data(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.user_id, HTTP_X_USER_ROLE='ISSUER')
        response = self.client.get('/api/institution/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'PENDING')

    def test_status_returns_404_when_no_application(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=str(uuid.uuid4()), HTTP_X_USER_ROLE='ISSUER')
        response = self.client.get('/api/institution/status/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_status_requires_authentication(self):
        response = self.client.get('/api/institution/status/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_status_fails_without_user_id_header(self):
        self.client.force_authenticate(user=MockUser())
        response = self.client.get('/api/institution/status/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Pending applications endpoint
# ---------------------------------------------------------------------------

class TestPendingApplicationsEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_id = str(uuid.uuid4())
        Institution.objects.create(
            user_id=uuid.uuid4(),
            name='Pending Hospital',
            institution_type=Institution.InstitutionType.HOSPITAL,
            country='Cameroon',
            city='Douala',
            contact_email='hospital@test.cm',
            status=Institution.Status.PENDING,
        )
        Institution.objects.create(
            user_id=uuid.uuid4(),
            name='Approved University',
            institution_type=Institution.InstitutionType.UNIVERSITY,
            country='Cameroon',
            city='Yaounde',
            contact_email='uni@test.cm',
            status=Institution.Status.APPROVED,
        )

    def test_admin_can_view_pending_applications(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/institution/pending/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Pending Hospital')

    def test_non_admin_cannot_view_pending(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=str(uuid.uuid4()), HTTP_X_USER_ROLE='ISSUER')
        response = self.client.get('/api/institution/pending/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_requires_authentication(self):
        response = self.client.get('/api/institution/pending/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pending_only_returns_pending_institutions(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/institution/pending/')
        statuses = [item['status'] for item in response.data]
        self.assertTrue(all(s == 'PENDING' for s in statuses))


# ---------------------------------------------------------------------------
# All institutions endpoint
# ---------------------------------------------------------------------------

class TestAllInstitutionsEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_id = str(uuid.uuid4())
        Institution.objects.create(
            user_id=uuid.uuid4(), name='Uni A',
            institution_type=Institution.InstitutionType.UNIVERSITY,
            country='Cameroon', city='Yaounde', contact_email='a@test.cm',
            status=Institution.Status.PENDING,
        )
        Institution.objects.create(
            user_id=uuid.uuid4(), name='Bank B',
            institution_type=Institution.InstitutionType.BANK,
            country='Cameroon', city='Douala', contact_email='b@test.cm',
            status=Institution.Status.APPROVED,
        )

    def test_admin_can_view_all_institutions(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/institution/all/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_non_admin_cannot_view_all(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=str(uuid.uuid4()), HTTP_X_USER_ROLE='ISSUER')
        response = self.client.get('/api/institution/all/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_all_institutions_requires_authentication(self):
        response = self.client.get('/api/institution/all/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Approve endpoint
# ---------------------------------------------------------------------------

class TestApproveEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_id = str(uuid.uuid4())
        self.institution = Institution.objects.create(
            user_id=uuid.uuid4(),
            name='Test Bank',
            institution_type=Institution.InstitutionType.BANK,
            country='Cameroon',
            city='Yaounde',
            contact_email='bank@test.cm',
            status=Institution.Status.PENDING,
        )

    def test_admin_can_approve_institution(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(f'/api/institution/{self.institution.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.institution.refresh_from_db()
        self.assertEqual(self.institution.status, Institution.Status.APPROVED)

    def test_approve_sets_approved_by_and_approved_at(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        self.client.put(f'/api/institution/{self.institution.id}/approve/')
        self.institution.refresh_from_db()
        self.assertEqual(str(self.institution.approved_by), self.admin_id)
        self.assertIsNotNone(self.institution.approved_at)

    def test_non_admin_cannot_approve(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=str(uuid.uuid4()), HTTP_X_USER_ROLE='ISSUER')
        response = self.client.put(f'/api/institution/{self.institution.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_approve_already_approved(self):
        self.institution.status = Institution.Status.APPROVED
        self.institution.save()
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(f'/api/institution/{self.institution.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_nonexistent_institution_returns_404(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(f'/api/institution/{uuid.uuid4()}/approve/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_approve_requires_authentication(self):
        response = self.client.put(f'/api/institution/{self.institution.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Reject endpoint
# ---------------------------------------------------------------------------

class TestRejectEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_id = str(uuid.uuid4())
        self.institution = Institution.objects.create(
            user_id=uuid.uuid4(),
            name='Test Notary',
            institution_type=Institution.InstitutionType.NOTARY,
            country='Cameroon',
            city='Bafoussam',
            contact_email='notary@test.cm',
            status=Institution.Status.PENDING,
        )

    def test_admin_can_reject_with_reason(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(
            f'/api/institution/{self.institution.id}/reject/',
            data={'reason': 'Documents are not valid'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.institution.refresh_from_db()
        self.assertEqual(self.institution.status, Institution.Status.REJECTED)
        self.assertEqual(self.institution.rejection_reason, 'Documents are not valid')

    def test_reject_fails_without_reason(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(
            f'/api/institution/{self.institution.id}/reject/',
            data={}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_admin_cannot_reject(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=str(uuid.uuid4()), HTTP_X_USER_ROLE='ISSUER')
        response = self.client.put(
            f'/api/institution/{self.institution.id}/reject/',
            data={'reason': 'Not valid'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_nonexistent_institution_returns_404(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(
            f'/api/institution/{uuid.uuid4()}/reject/',
            data={'reason': 'Not valid'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_requires_authentication(self):
        response = self.client.put(
            f'/api/institution/{self.institution.id}/reject/',
            data={'reason': 'Not valid'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Revoke endpoint
# ---------------------------------------------------------------------------

class TestRevokeEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_id = str(uuid.uuid4())
        self.institution = Institution.objects.create(
            user_id=uuid.uuid4(),
            name='Test Manufacturer',
            institution_type=Institution.InstitutionType.MANUFACTURER,
            country='Cameroon',
            city='Douala',
            contact_email='manufacturer@test.cm',
            status=Institution.Status.APPROVED,
        )

    def test_admin_can_revoke_approved_institution(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(
            f'/api/institution/{self.institution.id}/revoke/',
            data={'reason': 'Violated platform terms'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.institution.refresh_from_db()
        self.assertEqual(self.institution.status, Institution.Status.REVOKED)

    def test_cannot_revoke_pending_institution(self):
        self.institution.status = Institution.Status.PENDING
        self.institution.save()
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(
            f'/api/institution/{self.institution.id}/revoke/',
            data={'reason': 'Some reason'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revoke_fails_without_reason(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(
            f'/api/institution/{self.institution.id}/revoke/',
            data={}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_admin_cannot_revoke(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=str(uuid.uuid4()), HTTP_X_USER_ROLE='ISSUER')
        response = self.client.put(
            f'/api/institution/{self.institution.id}/revoke/',
            data={'reason': 'Not allowed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_revoke_nonexistent_institution_returns_404(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.put(
            f'/api/institution/{uuid.uuid4()}/revoke/',
            data={'reason': 'Gone'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoke_requires_authentication(self):
        response = self.client.put(
            f'/api/institution/{self.institution.id}/revoke/',
            data={'reason': 'Not allowed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Institution detail endpoint
# ---------------------------------------------------------------------------

class TestInstitutionDetailEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_id = str(uuid.uuid4())
        self.institution = Institution.objects.create(
            user_id=uuid.uuid4(),
            name='Detail Test University',
            institution_type=Institution.InstitutionType.UNIVERSITY,
            country='Cameroon',
            city='Yaounde',
            contact_email='detail@test.cm',
            status=Institution.Status.APPROVED,
        )

    def test_admin_can_view_institution_detail(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get(f'/api/institution/{self.institution.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Detail Test University')

    def test_non_admin_cannot_view_detail(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=str(uuid.uuid4()), HTTP_X_USER_ROLE='ISSUER')
        response = self.client.get(f'/api/institution/{self.institution.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_for_nonexistent_institution_returns_404(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ID=self.admin_id, HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get(f'/api/institution/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_requires_authentication(self):
        response = self.client.get(f'/api/institution/{self.institution.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

import io
import uuid
from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from verification_app.models import VerificationLog, FraudFlag


VALID_RESULTS = {'AUTHENTIC', 'NOT_AUTHENTIC', 'UNVERIFIABLE'}


def make_test_image(filename='test.png'):
    """Generate a valid 10x10 white PNG using PIL (available in this container)."""
    from PIL import Image
    img = Image.new('RGB', (10, 10), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return SimpleUploadedFile(filename, buf.getvalue(), content_type='image/png')


class MockUser:
    """Minimal user for bypassing JWT on the IsAuthenticated fraud_flags endpoint."""
    is_authenticated = True

    def __init__(self):
        self.id = uuid.uuid4()


class TestVerificationLogModel(TestCase):

    def test_log_created_successfully(self):
        item_id = uuid.uuid4()
        log = VerificationLog.objects.create(
            item_id=item_id,
            method=VerificationLog.Method.QR,
            result=VerificationLog.Result.AUTHENTIC,
            input_data=str(item_id),
        )
        self.assertIsNotNone(log.id)
        self.assertEqual(log.result, VerificationLog.Result.AUTHENTIC)
        self.assertEqual(log.method, VerificationLog.Method.QR)

    def test_log_str_representation(self):
        log = VerificationLog.objects.create(
            method=VerificationLog.Method.SERIAL,
            result=VerificationLog.Result.NOT_AUTHENTIC,
            input_data='TEST-SERIAL',
        )
        self.assertIn('SERIAL', str(log))
        self.assertIn('NOT_AUTHENTIC', str(log))

    def test_log_verified_at_auto_set(self):
        log = VerificationLog.objects.create(
            method=VerificationLog.Method.QR,
            result=VerificationLog.Result.AUTHENTIC,
        )
        self.assertIsNotNone(log.verified_at)


class TestFraudFlagModel(TestCase):

    def test_fraud_flag_created_successfully(self):
        item_id = uuid.uuid4()
        flag = FraudFlag.objects.create(
            item_id=item_id,
            verification_count=10,
            window_start=timezone.now(),
            window_end=timezone.now(),
        )
        self.assertIsNotNone(flag.id)
        self.assertEqual(flag.status, FraudFlag.FlagStatus.OPEN)

    def test_fraud_flag_str_representation(self):
        item_id = uuid.uuid4()
        flag = FraudFlag.objects.create(
            item_id=item_id,
            verification_count=5,
            window_start=timezone.now(),
            window_end=timezone.now(),
        )
        self.assertIn('OPEN', str(flag))
        self.assertIn(str(item_id), str(flag))

    def test_fraud_flag_default_status_is_open(self):
        flag = FraudFlag.objects.create(
            item_id=uuid.uuid4(),
            verification_count=0,
            window_start=timezone.now(),
            window_end=timezone.now(),
        )
        self.assertEqual(flag.status, FraudFlag.FlagStatus.OPEN)


class TestVerifyQREndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_verify_qr_with_valid_uuid_returns_200(self):
        item_id = str(uuid.uuid4())
        response = self.client.post('/api/verify/qr/', data={'qr_data': item_id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data['result'], VALID_RESULTS)

    def test_verify_qr_response_has_expected_fields(self):
        item_id = str(uuid.uuid4())
        response = self.client.post('/api/verify/qr/', data={'qr_data': item_id}, format='json')
        self.assertIn('result', response.data)
        self.assertIn('method', response.data)
        self.assertIn('message', response.data)
        self.assertIn('verified_at', response.data)

    def test_verify_qr_with_invalid_format_returns_not_authentic(self):
        response = self.client.post('/api/verify/qr/', data={'qr_data': 'not-a-uuid'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['result'], 'NOT_AUTHENTIC')

    def test_verify_qr_method_is_qr(self):
        item_id = str(uuid.uuid4())
        response = self.client.post('/api/verify/qr/', data={'qr_data': item_id}, format='json')
        self.assertEqual(response.data['method'], 'QR')

    def test_verify_qr_fails_without_qr_data(self):
        response = self.client.post('/api/verify/qr/', data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_qr_logs_verification(self):
        item_id = str(uuid.uuid4())
        initial_count = VerificationLog.objects.count()
        self.client.post('/api/verify/qr/', data={'qr_data': item_id}, format='json')
        self.assertEqual(VerificationLog.objects.count(), initial_count + 1)

    def test_verify_qr_logs_invalid_qr_as_not_authentic(self):
        self.client.post('/api/verify/qr/', data={'qr_data': 'garbage'}, format='json')
        log = VerificationLog.objects.latest('verified_at')
        self.assertEqual(log.result, VerificationLog.Result.NOT_AUTHENTIC)
        self.assertEqual(log.method, VerificationLog.Method.QR)

    def test_verify_qr_no_auth_required(self):
        item_id = str(uuid.uuid4())
        response = self.client.post('/api/verify/qr/', data={'qr_data': item_id}, format='json')
        self.assertNotIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])


class TestVerifySerialEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_verify_serial_returns_200(self):
        response = self.client.post('/api/verify/serial/', data={
            'serial_number': 'QNT-2024-CERT-ABCD1234',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data['result'], VALID_RESULTS)

    def test_verify_serial_response_has_method_serial(self):
        response = self.client.post('/api/verify/serial/', data={
            'serial_number': 'QNT-2024-CERT-ABCD1234',
        }, format='json')
        self.assertEqual(response.data['method'], 'SERIAL')

    def test_verify_serial_fails_without_serial_number(self):
        response = self.client.post('/api/verify/serial/', data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_serial_logs_verification(self):
        # Use a unique serial so Redis cache from a previous run doesn't skip logging.
        unique_serial = f'QNT-TEST-{uuid.uuid4().hex[:8].upper()}'
        initial_count = VerificationLog.objects.count()
        self.client.post('/api/verify/serial/', data={
            'serial_number': unique_serial,
        }, format='json')
        self.assertEqual(VerificationLog.objects.count(), initial_count + 1)

    def test_verify_serial_no_auth_required(self):
        response = self.client.post('/api/verify/serial/', data={
            'serial_number': 'QNT-2024-CERT-ABCD1234',
        }, format='json')
        self.assertNotIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])


class TestVerifySignatureEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_verify_signature_accepts_file_upload(self):
        pdf_content = b'%PDF-1.4 fake pdf content for testing purposes'
        pdf_file = SimpleUploadedFile('test.pdf', pdf_content, content_type='application/pdf')
        response = self.client.post('/api/verify/signature/', data={
            'document': pdf_file,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data['result'], VALID_RESULTS)

    def test_verify_signature_response_method_is_signature(self):
        pdf_content = b'%PDF-1.4 test content'
        pdf_file = SimpleUploadedFile('test.pdf', pdf_content, content_type='application/pdf')
        response = self.client.post('/api/verify/signature/', data={
            'document': pdf_file,
        }, format='multipart')
        self.assertEqual(response.data['method'], 'SIGNATURE')

    def test_verify_signature_fails_without_document(self):
        response = self.client.post('/api/verify/signature/', data={}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_signature_logs_verification(self):
        initial_count = VerificationLog.objects.count()
        pdf_file = SimpleUploadedFile('test.pdf', b'%PDF-1.4 content', content_type='application/pdf')
        self.client.post('/api/verify/signature/', data={'document': pdf_file}, format='multipart')
        self.assertEqual(VerificationLog.objects.count(), initial_count + 1)


class TestVerifyOCREndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_verify_ocr_accepts_image_upload(self):
        response = self.client.post('/api/verify/ocr/', data={'image': make_test_image()}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data['result'], VALID_RESULTS)

    def test_verify_ocr_response_has_method_ocr(self):
        response = self.client.post('/api/verify/ocr/', data={'image': make_test_image()}, format='multipart')
        self.assertEqual(response.data['method'], 'OCR')

    def test_verify_ocr_fails_without_image(self):
        response = self.client.post('/api/verify/ocr/', data={}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_ocr_returns_200_for_valid_image(self):
        # Logging only occurs when OCR extracts text; a blank image may return early.
        # Just verify the endpoint handles the request without error.
        response = self.client.post('/api/verify/ocr/', data={'image': make_test_image()}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestVerifyWatermarkEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_verify_watermark_accepts_image_upload(self):
        response = self.client.post('/api/verify/watermark/', data={'image': make_test_image()}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data['result'], VALID_RESULTS)

    def test_verify_watermark_response_has_method_watermark(self):
        response = self.client.post('/api/verify/watermark/', data={'image': make_test_image()}, format='multipart')
        self.assertEqual(response.data['method'], 'WATERMARK')

    def test_verify_watermark_fails_without_image(self):
        response = self.client.post('/api/verify/watermark/', data={}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_watermark_logs_verification(self):
        initial_count = VerificationLog.objects.count()
        self.client.post('/api/verify/watermark/', data={'image': make_test_image()}, format='multipart')
        self.assertEqual(VerificationLog.objects.count(), initial_count + 1)


class TestReportItemEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_report_item_succeeds(self):
        item_id = str(uuid.uuid4())
        response = self.client.post('/api/verify/report/', data={
            'item_id': item_id,
            'reason': 'This item appears to be counterfeit based on visual inspection.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_report_creates_fraud_flag(self):
        item_id = str(uuid.uuid4())
        initial_count = FraudFlag.objects.count()
        self.client.post('/api/verify/report/', data={
            'item_id': item_id,
            'reason': 'This item appears suspicious and may be counterfeit.',
        }, format='json')
        self.assertEqual(FraudFlag.objects.count(), initial_count + 1)

    def test_report_creates_verification_log(self):
        item_id = str(uuid.uuid4())
        initial_count = VerificationLog.objects.count()
        self.client.post('/api/verify/report/', data={
            'item_id': item_id,
            'reason': 'This item appears suspicious and may be counterfeit.',
        }, format='json')
        self.assertEqual(VerificationLog.objects.count(), initial_count + 1)

    def test_report_fails_with_short_reason(self):
        item_id = str(uuid.uuid4())
        response = self.client.post('/api/verify/report/', data={
            'item_id': item_id,
            'reason': 'Short',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_fails_without_item_id(self):
        response = self.client.post('/api/verify/report/', data={
            'reason': 'This looks counterfeit and suspicious.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_fails_without_reason(self):
        response = self.client.post('/api/verify/report/', data={
            'item_id': str(uuid.uuid4()),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_no_auth_required(self):
        response = self.client.post('/api/verify/report/', data={
            'item_id': str(uuid.uuid4()),
            'reason': 'This item appears to be counterfeit.',
        }, format='json')
        self.assertNotIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])


class TestVerificationHistoryEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.item_id = uuid.uuid4()
        VerificationLog.objects.create(
            item_id=self.item_id,
            method=VerificationLog.Method.QR,
            result=VerificationLog.Result.AUTHENTIC,
            input_data=str(self.item_id),
        )
        VerificationLog.objects.create(
            item_id=self.item_id,
            method=VerificationLog.Method.SERIAL,
            result=VerificationLog.Result.AUTHENTIC,
            input_data='SERIAL-001',
        )

    def test_admin_can_view_history(self):
        self.client.credentials(HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get(f'/api/verify/history/{self.item_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_non_admin_cannot_view_history(self):
        self.client.credentials(HTTP_X_USER_ROLE='ISSUER')
        response = self.client.get(f'/api/verify/history/{self.item_id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_role_header_returns_403(self):
        response = self.client.get(f'/api/verify/history/{self.item_id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_history_returns_empty_for_item_with_no_logs(self):
        self.client.credentials(HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get(f'/api/verify/history/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestFraudFlagsEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()
        FraudFlag.objects.create(
            item_id=uuid.uuid4(),
            verification_count=60,
            window_start=timezone.now(),
            window_end=timezone.now(),
        )

    def test_admin_can_view_fraud_flags(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/verify/flags/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_non_admin_cannot_view_fraud_flags(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ROLE='ISSUER')
        response = self.client.get('/api/verify/flags/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_fraud_flags_requires_authentication(self):
        response = self.client.get('/api/verify/flags/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_fraud_flag_data_has_expected_fields(self):
        self.client.force_authenticate(user=MockUser())
        self.client.credentials(HTTP_X_USER_ROLE='ADMIN')
        response = self.client.get('/api/verify/flags/')
        flag = response.data[0]
        self.assertIn('item_id', flag)
        self.assertIn('verification_count', flag)
        self.assertIn('status', flag)
        self.assertEqual(flag['status'], 'OPEN')


# ---------------------------------------------------------------------------
# Additional tests for ≥80% coverage
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
from verification_app.views import (
    get_verifier_ip,
    log_verification,
    build_result,
    check_blockchain,
    check_fraud_pattern,
    send_issuer_notification,
    get_cached_result,
    cache_result,
)


class TestHelperFunctionsDirect(TestCase):

    def test_get_verifier_ip_returns_remote_addr(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        self.assertEqual(get_verifier_ip(request), '127.0.0.1')

    def test_get_verifier_ip_prefers_x_forwarded_for_first_ip(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.5, 192.168.1.1'
        self.assertEqual(get_verifier_ip(request), '10.0.0.5')

    def test_log_verification_creates_db_record_with_correct_fields(self):
        item_id = uuid.uuid4()
        log = log_verification(
            item_id, None,
            VerificationLog.Method.QR,
            VerificationLog.Result.AUTHENTIC,
            'qr-data', '127.0.0.1',
        )
        self.assertEqual(log.item_id, item_id)
        self.assertEqual(log.method, VerificationLog.Method.QR)
        self.assertEqual(log.result, VerificationLog.Result.AUTHENTIC)
        self.assertEqual(log.verifier_ip, '127.0.0.1')

    def test_build_result_contains_all_expected_keys(self):
        result = build_result('AUTHENTIC', uuid.uuid4(), 'QR', 'message here')
        for key in ('result', 'item_id', 'method', 'message', 'item_details', 'verified_at'):
            self.assertIn(key, result)

    def test_build_result_with_none_item_id(self):
        result = build_result('NOT_AUTHENTIC', None, 'SERIAL', 'not found')
        self.assertIsNone(result['item_id'])

    def test_build_result_with_item_details(self):
        details = {'category': 'CERTIFICATE', 'issuer': 'Test'}
        result = build_result('AUTHENTIC', uuid.uuid4(), 'QR', 'ok', item_details=details)
        self.assertEqual(result['item_details']['category'], 'CERTIFICATE')

    def test_check_blockchain_returns_mock_when_service_unreachable(self):
        result = check_blockchain(item_id=uuid.uuid4())
        self.assertIn('exists', result)
        self.assertTrue(result['exists'])
        self.assertIn('item_details', result)

    def test_check_blockchain_with_serial_number_uses_serial_url(self):
        result = check_blockchain(serial_number='QNT-TEST-SERIAL-001')
        self.assertIn('exists', result)

    def test_check_blockchain_http_200_returns_response_json(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'exists': True, 'item_id': str(uuid.uuid4())}
        with patch('verification_app.views.requests.get', return_value=mock_resp):
            result = check_blockchain(item_id=uuid.uuid4())
        self.assertTrue(result['exists'])
        self.assertIn('item_id', result)

    def test_send_issuer_notification_does_not_raise(self):
        send_issuer_notification('test@example.com', uuid.uuid4(), 'QR')

    def test_get_cached_result_returns_none_when_redis_raises(self):
        with patch('verification_app.views.get_redis_client', side_effect=Exception('no redis')):
            result = get_cached_result('some-key')
        self.assertIsNone(result)

    def test_get_cached_result_returns_parsed_data_on_cache_hit(self):
        import json
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({'result': 'AUTHENTIC', 'method': 'QR'}).encode()
        with patch('verification_app.views.get_redis_client', return_value=mock_redis):
            result = get_cached_result('test-item-id')
        self.assertEqual(result['result'], 'AUTHENTIC')

    def test_cache_result_silently_handles_redis_error(self):
        with patch('verification_app.views.get_redis_client', side_effect=Exception('no redis')):
            cache_result('some-key', {'result': 'AUTHENTIC'})

    def test_cache_result_calls_setex_on_redis(self):
        mock_redis = MagicMock()
        with patch('verification_app.views.get_redis_client', return_value=mock_redis):
            cache_result('test-key', {'result': 'AUTHENTIC'})
        mock_redis.setex.assert_called_once()


class TestCheckFraudPattern(TestCase):

    def test_fraud_pattern_creates_flag_at_threshold(self):
        item_id = uuid.uuid4()
        for _ in range(50):
            VerificationLog.objects.create(
                item_id=item_id,
                method=VerificationLog.Method.QR,
                result=VerificationLog.Result.AUTHENTIC,
            )
        initial = FraudFlag.objects.count()
        check_fraud_pattern(item_id)
        self.assertEqual(FraudFlag.objects.count(), initial + 1)

    def test_fraud_pattern_flag_has_correct_item_id(self):
        item_id = uuid.uuid4()
        for _ in range(50):
            VerificationLog.objects.create(
                item_id=item_id,
                method=VerificationLog.Method.QR,
                result=VerificationLog.Result.AUTHENTIC,
            )
        check_fraud_pattern(item_id)
        flag = FraudFlag.objects.filter(item_id=item_id).first()
        self.assertIsNotNone(flag)
        self.assertEqual(flag.item_id, item_id)
        self.assertEqual(flag.status, FraudFlag.FlagStatus.OPEN)

    def test_fraud_pattern_no_flag_created_below_threshold(self):
        item_id = uuid.uuid4()
        for _ in range(49):
            VerificationLog.objects.create(
                item_id=item_id,
                method=VerificationLog.Method.QR,
                result=VerificationLog.Result.AUTHENTIC,
            )
        initial = FraudFlag.objects.count()
        check_fraud_pattern(item_id)
        self.assertEqual(FraudFlag.objects.count(), initial)

    def test_fraud_pattern_ignores_not_authentic_logs(self):
        item_id = uuid.uuid4()
        for _ in range(50):
            VerificationLog.objects.create(
                item_id=item_id,
                method=VerificationLog.Method.QR,
                result=VerificationLog.Result.NOT_AUTHENTIC,
            )
        initial = FraudFlag.objects.count()
        check_fraud_pattern(item_id)
        self.assertEqual(FraudFlag.objects.count(), initial)


class TestVerifyEndpointsAdvanced(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_verify_qr_returns_not_authentic_when_blockchain_finds_nothing(self):
        with patch('verification_app.views.check_blockchain', return_value={'exists': False}):
            with patch('verification_app.views.get_cached_result', return_value=None):
                response = self.client.post('/api/verify/qr/', data={
                    'qr_data': str(uuid.uuid4()),
                }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['result'], 'NOT_AUTHENTIC')

    def test_verify_qr_returns_cached_result_without_logging(self):
        item_id = str(uuid.uuid4())
        cached = {
            'result': 'AUTHENTIC', 'item_id': item_id,
            'method': 'QR', 'message': 'Cached QR result!',
            'item_details': None,
            'verified_at': timezone.now().isoformat(),
        }
        initial_count = VerificationLog.objects.count()
        with patch('verification_app.views.get_cached_result', return_value=cached):
            response = self.client.post('/api/verify/qr/', data={
                'qr_data': item_id,
            }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Cached QR result!')
        self.assertEqual(VerificationLog.objects.count(), initial_count)

    def test_verify_serial_returns_cached_result(self):
        serial = f'QNT-CACHED-{uuid.uuid4().hex[:8].upper()}'
        cached = {
            'result': 'AUTHENTIC', 'item_id': None,
            'method': 'SERIAL', 'message': 'Cached serial!',
            'item_details': None,
            'verified_at': timezone.now().isoformat(),
        }
        with patch('verification_app.views.get_cached_result', return_value=cached):
            response = self.client.post('/api/verify/serial/', data={
                'serial_number': serial,
            }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Cached serial!')

    def test_verify_serial_not_authentic_when_blockchain_returns_not_exists(self):
        with patch('verification_app.views.check_blockchain', return_value={'exists': False}):
            with patch('verification_app.views.get_cached_result', return_value=None):
                unique_serial = f'QNT-TEST-{uuid.uuid4().hex[:8].upper()}'
                response = self.client.post('/api/verify/serial/', data={
                    'serial_number': unique_serial,
                }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['result'], 'NOT_AUTHENTIC')

    def test_verify_serial_with_item_id_in_blockchain_response(self):
        item_id = str(uuid.uuid4())
        with patch('verification_app.views.check_blockchain', return_value={
            'exists': True,
            'item_id': item_id,
            'item_details': {'category': 'CERTIFICATE'},
        }):
            with patch('verification_app.views.get_cached_result', return_value=None):
                unique_serial = f'QNT-TEST-{uuid.uuid4().hex[:8].upper()}'
                response = self.client.post('/api/verify/serial/', data={
                    'serial_number': unique_serial,
                }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['result'], 'AUTHENTIC')

    def test_verify_qr_with_x_forwarded_for_header_succeeds(self):
        response = self.client.post(
            '/api/verify/qr/',
            data={'qr_data': str(uuid.uuid4())},
            format='json',
            HTTP_X_FORWARDED_FOR='192.168.1.100, 10.0.0.1',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_serial_with_x_forwarded_for_header(self):
        unique_serial = f'QNT-FWD-{uuid.uuid4().hex[:8].upper()}'
        response = self.client.post(
            '/api/verify/serial/',
            data={'serial_number': unique_serial},
            format='json',
            HTTP_X_FORWARDED_FOR='172.16.0.1',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

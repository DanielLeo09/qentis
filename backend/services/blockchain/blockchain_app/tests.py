from django.test import TestCase
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status
from .models import BlockchainRecord


class BlockchainStoreHashTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.store_url = '/api/blockchain/store/'
        self.valid_payload = {
            'item_hash':   'a' * 64,
            'category':    'ACADEMIC',
            'issuer_id':   'issuer-uuid-001',
            'issuer_name': 'ICT University',
        }

    @patch('blockchain_app.views.store_hash_on_chain')
    def test_store_hash_success(self, mock_store):
        mock_store.return_value = '0xabc123'
        response = self.client.post(self.store_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tx_hash', response.data)
        self.assertTrue(BlockchainRecord.objects.filter(item_hash='a' * 64).exists())

    @patch('blockchain_app.views.store_hash_on_chain')
    def test_store_duplicate_hash_fails(self, mock_store):
        mock_store.return_value = '0xabc123'
        self.client.post(self.store_url, self.valid_payload, format='json')
        response = self.client.post(self.store_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_store_hash_missing_fields(self):
        response = self.client.post(self.store_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_store_hash_invalid_category(self):
        payload = {**self.valid_payload, 'category': 'INVALID'}
        response = self.client.post(self.store_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('blockchain_app.views.store_hash_on_chain')
    def test_store_hash_blockchain_error(self, mock_store):
        mock_store.side_effect = Exception('Ganache connection failed')
        response = self.client.post(self.store_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('error', response.data)


class BlockchainVerifyHashTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.verify_url = '/api/blockchain/verify/'

    @patch('blockchain_app.views.verify_hash_on_chain')
    def test_verify_authentic(self, mock_verify):
        mock_verify.return_value = {
            'exists':        True,
            'revoked':       False,
            'category':      'ACADEMIC',
            'issuer_id':     'issuer-001',
            'issuer_name':   'ICT University',
            'timestamp':     1700000000,
            'revoke_reason': '',
        }
        response = self.client.post(
            self.verify_url,
            {'item_hash': 'a' * 64},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'AUTHENTIC')

    @patch('blockchain_app.views.verify_hash_on_chain')
    def test_verify_not_found(self, mock_verify):
        mock_verify.return_value = {
            'exists': False, 'revoked': False,
            'category': '', 'issuer_id': '',
            'issuer_name': '', 'timestamp': 0, 'revoke_reason': '',
        }
        response = self.client.post(
            self.verify_url,
            {'item_hash': 'b' * 64},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'NOT_AUTHENTIC')

    @patch('blockchain_app.views.verify_hash_on_chain')
    def test_verify_revoked(self, mock_verify):
        mock_verify.return_value = {
            'exists': True, 'revoked': True,
            'category': 'ACADEMIC', 'issuer_id': 'i1',
            'issuer_name': 'ICT', 'timestamp': 0,
            'revoke_reason': 'Fraudulent certificate',
        }
        response = self.client.post(
            self.verify_url,
            {'item_hash': 'c' * 64},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'NOT_AUTHENTIC')

    def test_verify_missing_hash(self):
        response = self.client.post(self.verify_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('blockchain_app.views.verify_hash_on_chain')
    def test_verify_blockchain_error(self, mock_verify):
        mock_verify.side_effect = Exception('Ganache connection failed')
        response = self.client.post(
            self.verify_url,
            {'item_hash': 'd' * 64},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('error', response.data)


class BlockchainRevokeHashTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.revoke_url = '/api/blockchain/revoke/'
        # Create a record to revoke
        self.record = BlockchainRecord.objects.create(
            item_hash   = 'e' * 64,
            category    = 'ACADEMIC',
            issuer_id   = 'issuer-001',
            issuer_name = 'ICT University',
            tx_hash     = '0xabc',
            status      = BlockchainRecord.Status.STORED,
        )

    @patch('blockchain_app.views.revoke_hash_on_chain')
    def test_revoke_success(self, mock_revoke):
        mock_revoke.return_value = '0xrevoke123'
        response = self.client.post(
            self.revoke_url,
            {'item_hash': 'e' * 64, 'reason': 'Diploma is fake'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tx_hash', response.data)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, BlockchainRecord.Status.REVOKED)

    def test_revoke_hash_not_found(self):
        response = self.client.post(
            self.revoke_url,
            {'item_hash': 'f' * 64, 'reason': 'Does not exist'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoke_missing_fields(self):
        response = self.client.post(self.revoke_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('blockchain_app.views.revoke_hash_on_chain')
    def test_revoke_blockchain_error(self, mock_revoke):
        mock_revoke.side_effect = Exception('Ganache connection failed')
        response = self.client.post(
            self.revoke_url,
            {'item_hash': 'e' * 64, 'reason': 'Test error'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


class BlockchainHealthCheckTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    @patch('blockchain_app.web3_client.get_web3')
    def test_health_check(self, mock_web3):
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_web3.return_value = mock_w3
        response = self.client.get('/api/blockchain/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['service'], 'blockchain')

    @patch('blockchain_app.web3_client.get_web3')
    def test_health_check_ganache_disconnected(self, mock_web3):
        mock_web3.side_effect = Exception('Cannot connect')
        response = self.client.get('/api/blockchain/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['ganache_connected'])


class Web3ClientTests(TestCase):

    @patch('blockchain_app.web3_client.Web3')
    def test_get_web3_connected(self, mock_web3_class):
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_web3_class.return_value = mock_instance
        from .web3_client import get_web3
        w3 = get_web3()
        self.assertTrue(w3.is_connected())

    @patch('blockchain_app.web3_client.Web3')
    def test_get_web3_not_connected(self, mock_web3_class):
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = False
        mock_web3_class.return_value = mock_instance
        from .web3_client import get_web3
        with self.assertRaises(ConnectionError):
            get_web3()

    @patch('blockchain_app.web3_client.Web3')
    def test_get_deployer_account(self, mock_web3_class):
        mock_w3 = MagicMock()
        mock_w3.eth.accounts = ['0xAccount0', '0xAccount1']
        from .web3_client import get_deployer_account
        account = get_deployer_account(mock_w3)
        self.assertEqual(account, '0xAccount0')
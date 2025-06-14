import unittest
import os
from unittest.mock import patch, MagicMock
import shield_remediation_switch

class TestShieldRemediationSwitch(unittest.TestCase):
    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        
        # Patch boto3 client
        self.mock_shield = patch('boto3.client').start()
        self.shield_mock = MagicMock()
        self.mock_shield.return_value = self.shield_mock
        
        # Set default env vars
        os.environ['DISTRIBUTION_ID'] = 'E123456789'
        os.environ['ENABLE_BLOCK'] = 'true'

    def tearDown(self):
        patch.stopall()
        os.environ.pop('DISTRIBUTION_ID', None)
        os.environ.pop('ENABLE_BLOCK', None)

    def test_count_mode_updates_to_block(self):
        """Test COUNT mode updates to BLOCK when ENABLE_BLOCK=true"""
        self.shield_mock.list_protections.return_value = {
            'Protections': [{'Id': 'protect-123'}]
        }
        self.shield_mock.describe_application_layer_automatic_response_configuration.return_value = {
            'ApplicationLayerAutomaticResponseConfiguration': {
                'Action': {'Count': {}}
            }
        }

        response = shield_remediation_switch.lambda_handler({}, self.mock_context)
        
        self.assertEqual(response['statusCode'], 200)
        self.shield_mock.update_application_layer_automatic_response_configuration.assert_called_once()

    def test_disabled_mode_updates_to_block(self):
        """Test DISABLED mode updates to BLOCK when ENABLE_BLOCK=true"""
        self.shield_mock.list_protections.return_value = {
            'Protections': [{'Id': 'protect-123'}]
        }
        self.shield_mock.describe_application_layer_automatic_response_configuration.return_value = {
            'ApplicationLayerAutomaticResponseConfiguration': {
                'Action': {}
            }
        }

        response = shield_remediation_switch.lambda_handler({}, self.mock_context)
        
        self.assertEqual(response['statusCode'], 200)
        self.shield_mock.update_application_layer_automatic_response_configuration.assert_called_once()

    def test_block_mode_no_changes(self):
        """Test BLOCK mode makes no changes"""
        self.shield_mock.list_protections.return_value = {
            'Protections': [{'Id': 'protect-123'}]
        }
        self.shield_mock.describe_application_layer_automatic_response_configuration.return_value = {
            'ApplicationLayerAutomaticResponseConfiguration': {
                'Action': {'Block': {}}
            }
        }

        response = shield_remediation_switch.lambda_handler({}, self.mock_context)
        
        self.assertEqual(response['statusCode'], 200)
        self.shield_mock.update_application_layer_automatic_response_configuration.assert_not_called()

    def test_enable_block_false_skips_changes(self):
        """Test ENABLE_BLOCK=false skips changes"""
        os.environ['ENABLE_BLOCK'] = 'false'
        self.shield_mock.list_protections.return_value = {
            'Protections': [{'Id': 'protect-123'}]
        }
        self.shield_mock.describe_application_layer_automatic_response_configuration.return_value = {
            'ApplicationLayerAutomaticResponseConfiguration': {
                'Action': {'Count': {}}
            }
        }

        response = shield_remediation_switch.lambda_handler({}, self.mock_context)
        
        self.assertEqual(response['statusCode'], 200)
        self.shield_mock.update_application_layer_automatic_response_configuration.assert_not_called()
        self.assertIn('ENABLE_BLOCK=false', response['body'])

    def test_missing_distribution_id(self):
        """Test missing DISTRIBUTION_ID returns error"""
        os.environ.pop('DISTRIBUTION_ID')
        
        response = shield_remediation_switch.lambda_handler({}, self.mock_context)
        
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('DISTRIBUTION_ID', response['body'])

    def test_protection_not_found(self):
        """Test protection not found returns error"""
        self.shield_mock.list_protections.return_value = {
            'Protections': []
        }

        response = shield_remediation_switch.lambda_handler({}, self.mock_context)
        
        self.assertEqual(response['statusCode'], 404)
        self.assertIn('No Shield protection found', response['body'])

if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure src and repo root are in path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, '..'))
src_dir = os.path.join(repo_root, 'src')

sys.path.append(repo_root)
sys.path.append(src_dir)

# Mock modules that cause import errors or side effects
sys.modules['cmd'] = MagicMock()
sys.modules['cmd.secrets'] = MagicMock()
sys.modules['cmd.secrets.fetch'] = MagicMock()
sys.modules['utils'] = MagicMock()
sys.modules['utils.const'] = MagicMock()
sys.modules['utils.sync_state_meta'] = MagicMock()
sys.modules['utils.phase_io'] = MagicMock()
sys.modules['utils.misc'] = MagicMock()

# Now import the target functions
from src.main import update_secret, create_secret

class TestSecretSync(unittest.TestCase):
    def setUp(self):
        self.api_instance = MagicMock()
        self.logger = MagicMock()
        self.secret_name = "test-secret"
        self.secret_namespace = "test-ns"
        self.secret_type = "Opaque"
        self.secret_data = {"key": "value"}

    def test_update_secret_calls_replace(self):
        existing_secret_mock = MagicMock()
        existing_secret_mock.metadata.resource_version = "12345"

        update_secret(
            self.api_instance,
            self.secret_name,
            self.secret_namespace,
            self.secret_type,
            self.secret_data,
            existing_secret_mock,
            self.logger
        )

        self.api_instance.replace_namespaced_secret.assert_called_once()
        args, kwargs = self.api_instance.replace_namespaced_secret.call_args
        self.assertEqual(kwargs['name'], self.secret_name)
        self.assertEqual(kwargs['namespace'], self.secret_namespace)
        self.assertEqual(kwargs['body'].metadata.name, self.secret_name)
        self.assertEqual(kwargs['body'].metadata.resource_version, "12345")
        self.assertEqual(kwargs['body'].data, self.secret_data)

        self.logger.info.assert_called_with(f"Updated secret {self.secret_name} in namespace {self.secret_namespace}")

    def test_create_secret_calls_create(self):
        create_secret(
             self.api_instance,
            self.secret_name,
            self.secret_namespace,
            self.secret_type,
            self.secret_data,
            self.logger
        )

        self.api_instance.create_namespaced_secret.assert_called_once()

    def test_update_secret_handles_exception(self):
        from kubernetes.client.rest import ApiException
        self.api_instance.replace_namespaced_secret.side_effect = ApiException("Boom")
        existing_secret_mock = MagicMock()
        existing_secret_mock.metadata.resource_version = "12345"

        update_secret(
            self.api_instance,
            self.secret_name,
            self.secret_namespace,
            self.secret_type,
            self.secret_data,
            existing_secret_mock,
            self.logger
        )

        self.logger.error.assert_called_once()
        args, _ = self.logger.error.call_args
        self.assertIn("Failed to update secret", args[0])

if __name__ == '__main__':
    unittest.main()

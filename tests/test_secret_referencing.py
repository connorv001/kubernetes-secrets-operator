
import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.append(os.path.abspath("src"))

from utils.secret_referencing import resolve_all_secrets, split_path_and_key, resolve_secret_reference

class TestSecretReferencing(unittest.TestCase):
    def setUp(self):
        self.phase = MagicMock()
        self.phase.get.return_value = []

    def test_split_path_and_key(self):
        self.assertEqual(split_path_and_key("key"), ("/", "key"))
        self.assertEqual(split_path_and_key("/path/key"), ("/path", "key"))
        self.assertEqual(split_path_and_key("/key"), ("/", "key"))

    def test_resolve_local_secret_in_dict(self):
        secrets_dict = {
            "dev": {
                "/": {"KEY": "value"}
            }
        }
        # resolve_secret_reference takes secrets_dict as Dict[str, Dict[str, Dict[str, str]]]
        # But wait, resolve_all_secrets constructs it. resolve_secret_reference signature matches.

        # Test direct call to resolve_secret_reference is hard because we need to construct the complex dict.
        # Let's test via resolve_all_secrets or mock the dict.

        val = resolve_secret_reference("KEY", secrets_dict, self.phase, "app", "dev")
        self.assertEqual(val, "value")

    def test_resolve_cross_env_secret_in_dict(self):
        secrets_dict = {
            "prod": {
                "/": {"KEY": "prod_value"}
            }
        }
        val = resolve_secret_reference("prod.KEY", secrets_dict, self.phase, "app", "dev")
        self.assertEqual(val, "prod_value")

    def test_resolve_all_secrets_fetching(self):
        # Setup phase mock to return secrets
        def side_effect(env_name, keys=None, app_name=None, tag=None, path='/'):
            results = []
            if env_name == "prod" and path == "/":
                for k in keys:
                    if k in ["API_KEY", "DB_PASS"]:
                        results.append({"key": k, "value": f"fetched_{k}", "path": path, "environment": env_name})
            if env_name == "prod" and path == "/backend":
                for k in keys:
                    if k in ["SECRET_1", "SECRET_2"]:
                        results.append({"key": k, "value": f"fetched_{k}", "path": path, "environment": env_name})
            return results

        self.phase.get.side_effect = side_effect

        input_value = "Key1: ${prod.API_KEY}, Key2: ${prod.DB_PASS}, Key3: ${prod./backend/SECRET_1}"
        all_secrets = [] # Empty known secrets

        resolved = resolve_all_secrets(input_value, all_secrets, self.phase, "app", "dev")

        self.assertIn("fetched_API_KEY", resolved)
        self.assertIn("fetched_DB_PASS", resolved)
        self.assertIn("fetched_SECRET_1", resolved)

        # Verify calls.
        # With current implementation (N+1), we expect 3 calls.
        # With optimization, we expect 2 calls (one for /, one for /backend).
        # But this test just verifies correctness of output.

if __name__ == '__main__':
    unittest.main()

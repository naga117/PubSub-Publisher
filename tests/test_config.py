import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pubsub_publisher import config


class TestConfig(unittest.TestCase):
    def test_load_save_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "config.json"
            with patch("pubsub_publisher.config.get_config_path", return_value=test_path):
                data = config.load_config()
                self.assertEqual(data["projects"], [])
                self.assertIsNone(data["last_project_id"])

                data = config.add_project(data, "proj1")
                config.save_config(data)

                saved = json.loads(test_path.read_text(encoding="utf-8"))
                self.assertIn("proj1", saved["projects"])
                self.assertEqual(saved["last_project_id"], "proj1")

                data = config.remove_project(data, "proj1")
                config.save_config(data)
                saved = json.loads(test_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["projects"], [])


if __name__ == "__main__":
    unittest.main()

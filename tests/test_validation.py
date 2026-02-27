import unittest

from pubsub_publisher.validators import normalize_attribute_rows, validate_required_fields


class TestValidation(unittest.TestCase):
    def test_required_fields(self) -> None:
        with self.assertRaises(ValueError):
            validate_required_fields("", "topic", "message")
        with self.assertRaises(ValueError):
            validate_required_fields("project", "", "message")
        with self.assertRaises(ValueError):
            validate_required_fields("project", "topic", "")

    def test_normalize_attributes(self) -> None:
        rows = (
            ("key1", "value1"),
            ("", ""),
            ("key2", "value2"),
        )
        result = normalize_attribute_rows(rows)
        self.assertEqual(result, {"key1": "value1", "key2": "value2"})

    def test_duplicate_attributes(self) -> None:
        rows = (("key", "v1"), ("key", "v2"))
        with self.assertRaises(ValueError):
            normalize_attribute_rows(rows)


if __name__ == "__main__":
    unittest.main()

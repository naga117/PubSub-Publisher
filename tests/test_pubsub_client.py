import unittest
from unittest.mock import MagicMock, patch

from pubsub_publisher.pubsub_client import publish_message


class TestPubSubClient(unittest.TestCase):
    @patch("pubsub_publisher.pubsub_client.pubsub_v1.PublisherClient")
    def test_publish_message(self, mock_client_class: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.topic_path.return_value = "projects/p/topics/t"
        mock_future = MagicMock()
        mock_future.result.return_value = "message-id-123"
        mock_client.publish.return_value = mock_future
        mock_client_class.return_value = mock_client

        message_id = publish_message(
            "project",
            "topic",
            "hello",
            {"k": "v"},
            None,
        )

        self.assertEqual(message_id, "message-id-123")
        mock_client.topic_path.assert_called_once_with("project", "topic")
        mock_client.publish.assert_called_once()


if __name__ == "__main__":
    unittest.main()

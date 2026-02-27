from typing import Dict, List, Optional

from google.cloud import pubsub_v1
from google.auth import load_credentials_from_file


def _get_client(json_credentials_path: Optional[str]) -> pubsub_v1.PublisherClient:
    if json_credentials_path:
        credentials, _ = load_credentials_from_file(json_credentials_path)
        return pubsub_v1.PublisherClient(credentials=credentials)
    return pubsub_v1.PublisherClient()


def publish_message(
    project_id: str,
    topic_name: str,
    message: str,
    attributes: Dict[str, str],
    json_credentials_path: Optional[str] = None,
) -> str:
    client = _get_client(json_credentials_path)
    topic_path = client.topic_path(project_id, topic_name)
    data = message.encode("utf-8")
    future = client.publish(topic_path, data, **attributes)
    return future.result()


def list_topics(
    project_id: str,
    json_credentials_path: Optional[str] = None,
) -> List[str]:
    client = _get_client(json_credentials_path)
    project_path = f"projects/{project_id}"
    topics = []
    for topic in client.list_topics(request={"project": project_path}):
        if topic.name:
            topics.append(topic.name.split("/topics/")[-1])
    topics.sort()
    return topics

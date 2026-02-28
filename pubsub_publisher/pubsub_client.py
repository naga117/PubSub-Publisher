from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

from google.cloud import pubsub_v1
from google.auth import load_credentials_from_file


_CLIENT_CACHE: Dict[Optional[str], pubsub_v1.PublisherClient] = {}
_CLIENT_CACHE_LOCK = Lock()


def _normalize_credentials_path(json_credentials_path: Optional[str]) -> Optional[str]:
    if not json_credentials_path:
        return None
    return str(Path(json_credentials_path).expanduser().resolve())


def _get_client(json_credentials_path: Optional[str]) -> pubsub_v1.PublisherClient:
    cache_key = _normalize_credentials_path(json_credentials_path)
    with _CLIENT_CACHE_LOCK:
        client = _CLIENT_CACHE.get(cache_key)
        if client is not None:
            return client

        if cache_key:
            credentials, _ = load_credentials_from_file(cache_key)
            client = pubsub_v1.PublisherClient(credentials=credentials)
        else:
            client = pubsub_v1.PublisherClient()

        _CLIENT_CACHE[cache_key] = client
        return client


def get_publisher_client(json_credentials_path: Optional[str] = None) -> pubsub_v1.PublisherClient:
    return _get_client(json_credentials_path)


def publish_message(
    project_id: str,
    topic_name: str,
    message: str,
    attributes: Dict[str, str],
    json_credentials_path: Optional[str] = None,
    client: Optional[pubsub_v1.PublisherClient] = None,
) -> str:
    publisher = client or _get_client(json_credentials_path)
    topic_path = publisher.topic_path(project_id, topic_name)
    data = message.encode("utf-8")
    future = publisher.publish(topic_path, data, **attributes)
    return future.result()


def list_topics(
    project_id: str,
    json_credentials_path: Optional[str] = None,
    client: Optional[pubsub_v1.PublisherClient] = None,
) -> List[str]:
    publisher = client or _get_client(json_credentials_path)
    project_path = f"projects/{project_id}"
    topics = []
    for topic in publisher.list_topics(request={"project": project_path}):
        if topic.name:
            topics.append(topic.name.split("/topics/")[-1])
    topics.sort()
    return topics

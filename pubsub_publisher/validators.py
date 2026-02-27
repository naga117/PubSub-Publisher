from typing import Dict, Tuple


def validate_required_fields(project_id: str, topic_name: str, message: str) -> None:
    if not project_id:
        raise ValueError("Project ID is required.")
    if not topic_name:
        raise ValueError("Topic name is required.")
    if not message:
        raise ValueError("Message is required.")


def validate_attributes(attributes: Dict[str, str]) -> None:
    for key in attributes:
        if not key:
            raise ValueError("Attribute key cannot be empty.")
    if len(set(attributes.keys())) != len(attributes.keys()):
        raise ValueError("Duplicate attribute key detected.")


def normalize_attribute_rows(rows: Tuple[Tuple[str, str], ...]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for key, value in rows:
        key = key.strip()
        if not key and not value:
            continue
        if not key:
            raise ValueError("Attribute key cannot be empty.")
        if key in result:
            raise ValueError(f"Duplicate attribute key: {key}")
        result[key] = value
    return result

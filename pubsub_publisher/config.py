import json
from pathlib import Path
from typing import Dict, Any, List

APP_NAME = "PubSubPublisher"


def get_config_path() -> Path:
    base_dir = Path.home() / "Library" / "Application Support" / APP_NAME
    return base_dir / "config.json"


def default_config() -> Dict[str, Any]:
    return {
        "projects": [],
        "last_project_id": None,
        "remember_last_project": True,
        "auto_sync_topics": False,
        "csv_delimiter": "auto",
    }


def load_config() -> Dict[str, Any]:
    path = get_config_path()
    if not path.exists():
        return default_config()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_config()

    projects = data.get("projects", [])
    if not isinstance(projects, list):
        projects = []

    last_project_id = data.get("last_project_id")
    if last_project_id is not None and not isinstance(last_project_id, str):
        last_project_id = None

    remember_last_project = data.get("remember_last_project", True)
    if not isinstance(remember_last_project, bool):
        remember_last_project = True

    auto_sync_topics = data.get("auto_sync_topics", False)
    if not isinstance(auto_sync_topics, bool):
        auto_sync_topics = False

    csv_delimiter = data.get("csv_delimiter", "auto")
    if csv_delimiter not in {"auto", "comma", "tab"}:
        csv_delimiter = "auto"

    return {
        "projects": projects,
        "last_project_id": last_project_id,
        "remember_last_project": remember_last_project,
        "auto_sync_topics": auto_sync_topics,
        "csv_delimiter": csv_delimiter,
    }


def save_config(config: Dict[str, Any]) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")


def add_project(config: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    project_id = project_id.strip()
    if not project_id:
        return config

    projects: List[str] = list(config.get("projects", []))
    if project_id not in projects:
        projects.append(project_id)

    config["projects"] = projects
    config["last_project_id"] = project_id
    return config


def remove_project(config: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    projects: List[str] = [p for p in config.get("projects", []) if p != project_id]
    config["projects"] = projects
    if config.get("last_project_id") == project_id:
        config["last_project_id"] = projects[0] if projects else None
    return config

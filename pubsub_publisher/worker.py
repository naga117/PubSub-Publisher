import csv
from typing import Dict, Optional

from PyQt6.QtCore import QThread, pyqtSignal


class PublishWorker(QThread):
    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        project_id: str,
        topic_name: str,
        message: str,
        attributes: Dict[str, str],
        json_credentials_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.project_id = project_id
        self.topic_name = topic_name
        self.message = message
        self.attributes = attributes
        self.json_credentials_path = json_credentials_path

    def run(self) -> None:
        try:
            from .pubsub_client import publish_message

            message_id = publish_message(
                self.project_id,
                self.topic_name,
                self.message,
                self.attributes,
                self.json_credentials_path,
            )
            self.success.emit(message_id)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class ListTopicsWorker(QThread):
    success = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(
        self,
        project_id: str,
        json_credentials_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.project_id = project_id
        self.json_credentials_path = json_credentials_path

    def run(self) -> None:
        try:
            from .pubsub_client import list_topics

            topics = list_topics(self.project_id, self.json_credentials_path)
            self.success.emit(topics)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class BulkPublishWorker(QThread):
    log = pyqtSignal(str, str, str)
    summary = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(
        self,
        project_id: str,
        topic_name: str,
        file_path: str,
        delimiter: str,
        json_credentials_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.project_id = project_id
        self.topic_name = topic_name
        self.file_path = file_path
        self.delimiter = delimiter
        self.json_credentials_path = json_credentials_path

    def run(self) -> None:
        success_count = 0
        error_count = 0
        try:
            from .pubsub_client import publish_message

            with open(self.file_path, "r", encoding="utf-8", newline="") as handle:
                sample = handle.read(2048)
                handle.seek(0)
                if self.delimiter == "tab":
                    dialect = csv.excel_tab
                elif self.delimiter == "comma":
                    dialect = csv.excel
                elif self.file_path.lower().endswith(".tsv"):
                    dialect = csv.excel_tab
                else:
                    dialect = csv.Sniffer().sniff(sample)
                reader = csv.DictReader(handle, dialect=dialect)
                if not reader.fieldnames or "message" not in reader.fieldnames:
                    self.error.emit("CSV/TSV must include a 'message' column.")
                    return
                for row in reader:
                    message = (row.get("message") or "").strip()
                    if not message:
                        error_count += 1
                        self.log.emit(
                            "ERROR",
                            "",
                            f"line {reader.line_num}: empty message",
                        )
                        continue
                    attributes = {
                        key: str(value)
                        for key, value in row.items()
                        if key != "message" and value not in (None, "")
                    }
                    try:
                        message_id = publish_message(
                            self.project_id,
                            self.topic_name,
                            message,
                            attributes,
                            self.json_credentials_path,
                        )
                        success_count += 1
                        self.log.emit("SUCCESS", message_id, "")
                    except Exception as exc:  # noqa: BLE001
                        error_count += 1
                        self.log.emit(
                            "ERROR",
                            "",
                            f"line {reader.line_num}: {exc}",
                        )
        except csv.Error as exc:
            self.error.emit(f"CSV parse error: {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
            return

        self.summary.emit(success_count, error_count)

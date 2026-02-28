import csv
import html
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QSize, QTimer, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStyle,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config import add_project, load_config, remove_project, save_config
from .models import LogEntry
from .validators import normalize_attribute_rows, validate_required_fields
from .worker import BulkPublishWorker, ListTopicsWorker, PublishWorker


class AttributeRow(QWidget):
    def __init__(self, on_remove) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Key")
        layout.addWidget(self.key_input)

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Value")
        layout.addWidget(self.value_input)

        remove_btn = QPushButton("Remove")
        remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        remove_btn.setIconSize(QSize(16, 16))
        remove_btn.setToolTip("Remove attribute")
        remove_btn.clicked.connect(on_remove)
        layout.addWidget(remove_btn)

    def values(self) -> Tuple[str, str]:
        return self.key_input.text().strip(), self.value_input.text()


class CompactComboBox(QComboBox):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMaxVisibleItems(12)

    def showPopup(self) -> None:
        # Native macOS combo popups can behave inconsistently in bundled apps when
        # we force custom view sizing. Let Qt/macOS handle the popup there.
        if sys.platform == "darwin":
            super().showPopup()
            return
        view = self.view()
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        view.setUniformItemSizes(True)
        view.setMaximumHeight(180)
        view.setMinimumWidth(self.width())
        view.setStyleSheet("")
        super().showPopup()


class ProjectConfigDialog(QDialog):
    def __init__(self, parent: QWidget, config: Dict[str, object]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Project Configuration")
        self.resize(420, 320)
        self.config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(QLabel("Projects"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        add_btn = QPushButton("Add")
        add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.setToolTip("Add project")
        add_btn.clicked.connect(self._add_project)
        btn_row.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        remove_btn.setIconSize(QSize(16, 16))
        remove_btn.setToolTip("Remove selected project")
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        close_btn = QPushButton("Close")
        close_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._load_projects()

    def _load_projects(self) -> None:
        self.list_widget.clear()
        for project in self.config.get("projects", []):
            if isinstance(project, str):
                self.list_widget.addItem(QListWidgetItem(project))

    def _add_project(self) -> None:
        project_id, ok = QInputDialog.getText(self, "Add Project", "Project ID")
        if not ok:
            return
        project_id = project_id.strip()
        if not project_id:
            QMessageBox.warning(self, "Invalid Project", "Project ID cannot be empty.")
            return
        self.config = add_project(self.config, project_id)
        save_config(self.config)
        self._load_projects()

    def _remove_selected(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "Remove Project", "No project selected.")
            return
        project_id = item.text()
        confirm = QMessageBox.question(
            self,
            "Remove Project",
            f"Remove project '{project_id}'?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.config = remove_project(self.config, project_id)
        save_config(self.config)
        self._load_projects()


class MainWindow(QMainWindow):
    PROJECT_CHANGE_DEBOUNCE_MS = 400

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PubSub Publisher")
        self.resize(900, 650)

        self._apply_compact_style()

        self.config = load_config()
        self.logs: List[LogEntry] = []
        self.worker: Optional[PublishWorker] = None
        self.topics_worker: Optional[ListTopicsWorker] = None
        self.bulk_topics_worker: Optional[ListTopicsWorker] = None
        self.bulk_worker: Optional[BulkPublishWorker] = None
        self.attribute_rows: List[AttributeRow] = []
        self.auth_state = {"use_json": False, "json_path": ""}
        self.auth_widgets: Dict[str, Tuple[QCheckBox, QLineEdit, QPushButton]] = {}
        self.logs_views: List[QListWidget] = []
        self.settings_widgets: Dict[str, QWidget] = {}
        self.publish_status_label: Optional[QLabel] = None
        self.bulk_status_label: Optional[QLabel] = None
        self.bulk_progress_counts = {"success": 0, "error": 0}
        self._project_change_timers: Dict[str, QTimer] = {}
        self._pending_project_text = {"publish": "", "bulk": ""}
        self._last_auto_synced_project: Dict[str, Optional[str]] = {"publish": None, "bulk": None}

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 22, 22, 22)
        root_layout.setSpacing(6)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        publish_tab = QWidget()
        publish_layout = QVBoxLayout(publish_tab)
        publish_layout.setContentsMargins(20, 20, 20, 20)
        publish_layout.setSpacing(8)

        publish_layout.addLayout(self._build_project_panel())
        publish_layout.addLayout(self._build_message_panel())
        publish_layout.addLayout(self._build_attributes_panel())
        publish_layout.addLayout(self._build_actions_panel())
        publish_layout.addWidget(self._build_publish_status_bar())
        publish_layout.addLayout(self._build_logs_panel())

        self.tabs.addTab(publish_tab, "Publish")

        bulk_tab = QWidget()
        bulk_layout = QVBoxLayout(bulk_tab)
        bulk_layout.setContentsMargins(20, 20, 20, 20)
        bulk_layout.setSpacing(8)

        bulk_layout.addLayout(self._build_bulk_project_panel())
        bulk_layout.addWidget(self._build_bulk_format_note())
        bulk_layout.addLayout(self._build_bulk_file_panel())
        bulk_layout.addLayout(self._build_bulk_actions_panel())
        bulk_layout.addWidget(self._build_bulk_status_bar())
        bulk_layout.addLayout(self._build_logs_panel())

        self.tabs.addTab(bulk_tab, "Bulk Publish")

        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(10)

        settings_layout.addWidget(QLabel("Authentication"))
        settings_layout.addLayout(self._build_auth_panel("settings"))
        settings_layout.addWidget(QLabel("Application Settings"))
        settings_layout.addLayout(self._build_settings_panel())
        settings_layout.addStretch()

        self.tabs.addTab(settings_tab, "Settings")

        self._project_change_timers = {
            "publish": self._create_project_change_timer("publish"),
            "bulk": self._create_project_change_timer("bulk"),
        }
        self._load_projects()
        self._load_settings()
        self._set_publish_status("Idle")
        self._set_bulk_status("Idle")

    def _apply_compact_style(self) -> None:
        # Use native macOS styling for colors and dropdowns.
        self.setStyleSheet("")

    def _build_project_panel(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.addWidget(QLabel("Project ID"), 0, 0)

        self.project_combo = CompactComboBox()
        self.project_combo.setEditable(True)
        self.project_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.project_combo.currentTextChanged.connect(
            lambda project_id: self._queue_project_change("publish", project_id)
        )
        layout.addWidget(self.project_combo, 0, 1, 1, 2)

        config_btn = QPushButton("Projects")
        config_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        config_btn.setIconSize(QSize(16, 16))
        config_btn.setToolTip("Manage projects")
        config_btn.clicked.connect(self._open_project_config)
        layout.addWidget(config_btn, 0, 3)

        layout.addWidget(QLabel("Topic Name"), 1, 0)
        self.topic_combo = CompactComboBox()
        self.topic_combo.setEditable(True)
        self.topic_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        layout.addWidget(self.topic_combo, 1, 1, 1, 2)

        self.sync_btn = QPushButton("Sync")
        self.sync_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.sync_btn.setIconSize(QSize(16, 16))
        self.sync_btn.setToolTip("Sync topics")
        self.sync_btn.clicked.connect(self._sync_topics)
        layout.addWidget(self.sync_btn, 1, 3)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 0)

        return layout

    def _build_message_panel(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.addWidget(QLabel("Message"), 0, 0)
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Enter message to publish")
        self.message_input.setFixedHeight(120)
        layout.addWidget(self.message_input, 0, 1, 1, 3)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 0)
        return layout

    def _build_attributes_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.addWidget(QLabel("Attributes"))

        self.attributes_container = QWidget()
        self.attributes_layout = QVBoxLayout(self.attributes_container)
        self.attributes_layout.setContentsMargins(0, 0, 0, 0)
        self.attributes_layout.setSpacing(6)
        layout.addWidget(self.attributes_container)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        add_attr_btn = QPushButton("Add Attribute")
        add_attr_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        add_attr_btn.setIconSize(QSize(16, 16))
        add_attr_btn.setToolTip("Add attribute")
        add_attr_btn.clicked.connect(self._add_attribute_row)
        btn_row.addWidget(add_attr_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return layout

    def _build_auth_panel(self, kind: str) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(6)
        use_json_checkbox = QCheckBox("Use Service Account JSON")
        use_json_checkbox.stateChanged.connect(lambda: self._toggle_json_picker(kind))
        layout.addWidget(use_json_checkbox, 0, 0)

        json_path_input = QLineEdit()
        json_path_input.setReadOnly(True)
        json_path_input.setEnabled(False)
        layout.addWidget(json_path_input, 0, 1)

        json_browse_btn = QPushButton("Browse")
        json_browse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        json_browse_btn.setIconSize(QSize(16, 16))
        json_browse_btn.setToolTip("Select JSON file")
        json_browse_btn.setEnabled(False)
        json_browse_btn.clicked.connect(lambda: self._select_json_file(kind))
        layout.addWidget(json_browse_btn, 0, 2)

        self.auth_widgets[kind] = (use_json_checkbox, json_path_input, json_browse_btn)
        self._apply_auth_state()

        return layout

    def _build_settings_panel(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        remember_cb = QCheckBox("Remember last selected project")
        remember_cb.stateChanged.connect(self._on_settings_changed)
        layout.addWidget(remember_cb, 0, 0, 1, 2)

        auto_sync_cb = QCheckBox("Auto-sync topics when project changes")
        auto_sync_cb.stateChanged.connect(self._on_settings_changed)
        layout.addWidget(auto_sync_cb, 1, 0, 1, 2)

        layout.addWidget(QLabel("CSV/TSV delimiter"), 2, 0)
        delimiter_combo = QComboBox()
        delimiter_combo.addItems(["Auto (detect)", "Comma (,)", "Tab (\\t)"])
        delimiter_combo.currentIndexChanged.connect(self._on_settings_changed)
        layout.addWidget(delimiter_combo, 2, 1)

        self.settings_widgets = {
            "remember_last_project": remember_cb,
            "auto_sync_topics": auto_sync_cb,
            "csv_delimiter": delimiter_combo,
        }

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        return layout

    def _build_actions_panel(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(6)
        self.publish_btn = QPushButton("Publish")
        self.publish_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.publish_btn.setIconSize(QSize(16, 16))
        self.publish_btn.setToolTip("Publish message")
        self.publish_btn.clicked.connect(self._publish_message)
        layout.addWidget(self.publish_btn)
        layout.addStretch()
        return layout

    def _build_publish_status_bar(self) -> QLabel:
        self.publish_status_label = QLabel()
        self.publish_status_label.setWordWrap(True)
        self.publish_status_label.setStyleSheet("padding: 2px 0;")
        return self.publish_status_label

    def _build_bulk_project_panel(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.addWidget(QLabel("Project ID"), 0, 0)

        self.bulk_project_combo = CompactComboBox()
        self.bulk_project_combo.setEditable(True)
        self.bulk_project_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.bulk_project_combo.currentTextChanged.connect(
            lambda project_id: self._queue_project_change("bulk", project_id)
        )
        layout.addWidget(self.bulk_project_combo, 0, 1, 1, 2)

        config_btn = QPushButton("Projects")
        config_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        config_btn.setIconSize(QSize(16, 16))
        config_btn.setToolTip("Manage projects")
        config_btn.clicked.connect(self._open_project_config)
        layout.addWidget(config_btn, 0, 3)

        layout.addWidget(QLabel("Topic Name"), 1, 0)
        self.bulk_topic_combo = CompactComboBox()
        self.bulk_topic_combo.setEditable(True)
        self.bulk_topic_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        layout.addWidget(self.bulk_topic_combo, 1, 1, 1, 2)

        self.bulk_sync_btn = QPushButton("Sync")
        self.bulk_sync_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.bulk_sync_btn.setIconSize(QSize(16, 16))
        self.bulk_sync_btn.setToolTip("Sync topics")
        self.bulk_sync_btn.clicked.connect(self._sync_topics_bulk)
        layout.addWidget(self.bulk_sync_btn, 1, 3)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 0)

        return layout

    def _build_bulk_file_panel(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.addWidget(QLabel("Messages File"), 0, 0)

        self.bulk_file_input = QLineEdit()
        self.bulk_file_input.setReadOnly(True)
        layout.addWidget(self.bulk_file_input, 0, 1, 1, 2)

        browse_btn = QPushButton("Browse")
        browse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        browse_btn.setIconSize(QSize(16, 16))
        browse_btn.setToolTip("Select messages file")
        browse_btn.clicked.connect(self._select_bulk_file)
        layout.addWidget(browse_btn, 0, 3)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 0)
        return layout

    def _build_bulk_format_note(self) -> QLabel:
        note = QLabel(
            "Bulk file format: first row must be headers and include a 'message' column. "
            "Each row publishes one message. Any other columns are sent as attributes "
            "(column name = attribute key, cell value = attribute value). Empty attribute values are ignored."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #555;")
        note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return note

    def _build_bulk_actions_panel(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(6)
        self.bulk_publish_btn = QPushButton("Publish File")
        self.bulk_publish_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.bulk_publish_btn.setIconSize(QSize(16, 16))
        self.bulk_publish_btn.setToolTip("Publish all messages in the file")
        self.bulk_publish_btn.clicked.connect(self._publish_bulk_file)
        layout.addWidget(self.bulk_publish_btn)
        layout.addStretch()
        return layout

    def _build_bulk_status_bar(self) -> QLabel:
        self.bulk_status_label = QLabel()
        self.bulk_status_label.setWordWrap(True)
        self.bulk_status_label.setStyleSheet("padding: 2px 0;")
        return self.bulk_status_label

    def _build_logs_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.addWidget(QLabel("Logs"))

        logs_view = QListWidget()
        layout.addWidget(logs_view)
        self.logs_views.append(logs_view)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        clear_btn = QPushButton("Clear All")
        clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.setToolTip("Clear inputs and logs")
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        export_btn.setIconSize(QSize(16, 16))
        export_btn.setToolTip("Export logs to CSV")
        export_btn.clicked.connect(self._export_logs)
        btn_row.addWidget(export_btn)
        btn_row.addStretch()

        layout.addLayout(btn_row)
        return layout

    def _load_projects(self) -> None:
        self.project_combo.clear()
        self.bulk_project_combo.clear()
        projects = [p for p in self.config.get("projects", []) if isinstance(p, str)]
        self.project_combo.addItems(projects)
        self.bulk_project_combo.addItems(projects)
        last_project = self.config.get("last_project_id")
        if self.config.get("remember_last_project", True) and last_project in projects:
            self.project_combo.setCurrentText(last_project)
            self.bulk_project_combo.setCurrentText(last_project)

    def _status_color(self, message: str) -> str:
        text = message.lower()
        if "fail" in text or "error" in text:
            return "#c62828"
        if "publishing" in text or "syncing" in text or "started" in text:
            return "#1565c0"
        if "success" in text or "complete" in text or "synced" in text or "ready" in text:
            return "#2e7d32"
        return "#616161"

    def _render_status_line(self, label: Optional[QLabel], message: str) -> None:
        if label is None:
            return
        color = self._status_color(message)
        safe = html.escape(message)
        label.setText(
            f"<span style='color:{color}; font-weight:600'>●</span> "
            f"<span style='color:{color}'>Status: {safe}</span>"
        )
        label.setToolTip(message)

    def _set_publish_status(self, message: str) -> None:
        self._render_status_line(self.publish_status_label, message)

    def _set_bulk_status(self, message: str) -> None:
        self._render_status_line(self.bulk_status_label, message)

    def _save_config(self) -> None:
        save_config(self.config)

    def _create_project_change_timer(self, source: str) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self.PROJECT_CHANGE_DEBOUNCE_MS)
        timer.timeout.connect(lambda: self._on_project_changed(source))
        return timer

    def _queue_project_change(self, source: str, project_id: str) -> None:
        self._pending_project_text[source] = project_id
        timer = self._project_change_timers.get(source)
        if timer:
            timer.start()

    def _on_project_changed(self, source: str) -> None:
        project_id = self._pending_project_text.get(source, "").strip()
        if not project_id:
            return

        if self.config.get("remember_last_project", True):
            if self.config.get("last_project_id") != project_id:
                self.config["last_project_id"] = project_id
                self._save_config()

        if not self.config.get("auto_sync_topics", False):
            return

        if self._last_auto_synced_project.get(source) == project_id:
            return

        if source == "publish":
            self._sync_topics()
        elif source == "bulk":
            self._sync_topics_bulk()

    def _open_project_config(self) -> None:
        dialog = ProjectConfigDialog(self, self.config)
        dialog.exec()
        self.config = load_config()
        self._load_projects()

    def _add_attribute_row(self) -> None:
        row = AttributeRow(lambda: self._remove_attribute_row(row))
        self.attribute_rows.append(row)
        self.attributes_layout.addWidget(row)

    def _remove_attribute_row(self, row: AttributeRow) -> None:
        if row in self.attribute_rows:
            self.attribute_rows.remove(row)
            row.setParent(None)
            row.deleteLater()

    def _toggle_json_picker(self, kind: str) -> None:
        checkbox, _, _ = self.auth_widgets[kind]
        enabled = checkbox.isChecked()
        self.auth_state["use_json"] = enabled
        self._apply_auth_state()

    def _apply_auth_state(self) -> None:
        for checkbox, path_input, browse_btn in self.auth_widgets.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(self.auth_state["use_json"])
            checkbox.blockSignals(False)
            path_input.setEnabled(self.auth_state["use_json"])
            browse_btn.setEnabled(self.auth_state["use_json"])
            path_input.setText(self.auth_state["json_path"])

    def _load_settings(self) -> None:
        remember = self.config.get("remember_last_project", True)
        auto_sync = self.config.get("auto_sync_topics", False)
        delimiter = self.config.get("csv_delimiter", "auto")

        remember_cb = self.settings_widgets.get("remember_last_project")
        auto_sync_cb = self.settings_widgets.get("auto_sync_topics")
        delimiter_combo = self.settings_widgets.get("csv_delimiter")

        if isinstance(remember_cb, QCheckBox):
            remember_cb.setChecked(remember)
        if isinstance(auto_sync_cb, QCheckBox):
            auto_sync_cb.setChecked(auto_sync)
        if isinstance(delimiter_combo, QComboBox):
            index = {"auto": 0, "comma": 1, "tab": 2}.get(delimiter, 0)
            delimiter_combo.setCurrentIndex(index)

    def _on_settings_changed(self) -> None:
        remember_cb = self.settings_widgets.get("remember_last_project")
        auto_sync_cb = self.settings_widgets.get("auto_sync_topics")
        delimiter_combo = self.settings_widgets.get("csv_delimiter")

        if isinstance(remember_cb, QCheckBox):
            self.config["remember_last_project"] = remember_cb.isChecked()
            if not self.config["remember_last_project"]:
                self.config["last_project_id"] = None
        if isinstance(auto_sync_cb, QCheckBox):
            self.config["auto_sync_topics"] = auto_sync_cb.isChecked()
        if isinstance(delimiter_combo, QComboBox):
            self.config["csv_delimiter"] = {0: "auto", 1: "comma", 2: "tab"}.get(
                delimiter_combo.currentIndex(), "auto"
            )

        self._save_config()

    def _select_json_file(self, kind: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Service Account JSON",
            "",
            "JSON Files (*.json)",
        )
        if path:
            self.auth_state["json_path"] = path
            self._apply_auth_state()

    def _collect_attributes(self) -> Dict[str, str]:
        rows = [row.values() for row in self.attribute_rows]
        return normalize_attribute_rows(tuple(rows))

    def _validate_inputs(self) -> Dict[str, object]:
        project_id = self.project_combo.currentText().strip()
        topic_name = self.topic_combo.currentText().strip()
        message = self.message_input.toPlainText().strip()

        validate_required_fields(project_id, topic_name, message)

        attributes = self._collect_attributes()
        json_path = self._get_auth_path()

        return {
            "project_id": project_id,
            "topic_name": topic_name,
            "message": message,
            "attributes": attributes,
            "json_path": json_path,
        }

    def _get_auth_path(self) -> Optional[str]:
        if not self.auth_state["use_json"]:
            return None
        json_path = self.auth_state["json_path"]
        if not json_path:
            raise ValueError("Select a service account JSON file.")
        if not Path(json_path).exists():
            raise ValueError("Selected JSON file does not exist.")
        return json_path

    def _sync_topics(self) -> None:
        project_id = self.project_combo.currentText().strip()
        if not project_id:
            QMessageBox.warning(self, "Sync Topics", "Project ID is required.")
            return

        try:
            json_path = self._get_auth_path()
        except ValueError as exc:
            QMessageBox.warning(self, "Sync Topics", str(exc))
            return

        self.sync_btn.setEnabled(False)
        self._set_publish_status("Syncing topics...")
        self._last_auto_synced_project["publish"] = project_id
        self.topics_worker = ListTopicsWorker(project_id, json_path)
        self.topics_worker.success.connect(self._on_topics_loaded)
        self.topics_worker.error.connect(self._on_topics_error)
        self.topics_worker.finished.connect(self._on_topics_finished)
        self.topics_worker.start()

    def _on_topics_loaded(self, topics: List[str]) -> None:
        current = self.topic_combo.currentText().strip()
        self.topic_combo.clear()
        self.topic_combo.addItems(topics)
        if current:
            self.topic_combo.setCurrentText(current)
        self._set_publish_status(f"Topics synced ({len(topics)} found).")

    def _on_topics_error(self, error: str) -> None:
        self._set_publish_status(f"Topic sync failed: {error}")
        QMessageBox.warning(self, "Sync Topics", error)

    def _on_topics_finished(self) -> None:
        self.sync_btn.setEnabled(True)
        self.topics_worker = None

    def _sync_topics_bulk(self) -> None:
        project_id = self.bulk_project_combo.currentText().strip()
        if not project_id:
            QMessageBox.warning(self, "Sync Topics", "Project ID is required.")
            return
        try:
            json_path = self._get_auth_path()
        except ValueError as exc:
            QMessageBox.warning(self, "Sync Topics", str(exc))
            return

        self.bulk_sync_btn.setEnabled(False)
        self._set_bulk_status("Syncing topics...")
        self._last_auto_synced_project["bulk"] = project_id
        self.bulk_topics_worker = ListTopicsWorker(project_id, json_path)
        self.bulk_topics_worker.success.connect(self._on_bulk_topics_loaded)
        self.bulk_topics_worker.error.connect(self._on_bulk_topics_error)
        self.bulk_topics_worker.finished.connect(self._on_bulk_topics_finished)
        self.bulk_topics_worker.start()

    def _on_bulk_topics_loaded(self, topics: List[str]) -> None:
        current = self.bulk_topic_combo.currentText().strip()
        self.bulk_topic_combo.clear()
        self.bulk_topic_combo.addItems(topics)
        if current:
            self.bulk_topic_combo.setCurrentText(current)
        self._set_bulk_status(f"Topics synced ({len(topics)} found).")

    def _on_bulk_topics_error(self, error: str) -> None:
        self._set_bulk_status(f"Topic sync failed: {error}")
        QMessageBox.warning(self, "Sync Topics", error)

    def _on_bulk_topics_finished(self) -> None:
        self.bulk_sync_btn.setEnabled(True)
        self.bulk_topics_worker = None

    def _select_bulk_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Messages File",
            "",
            "CSV/TSV Files (*.csv *.tsv);;All Files (*)",
        )
        if path:
            self.bulk_file_input.setText(path)

    def _publish_bulk_file(self) -> None:
        project_id = self.bulk_project_combo.currentText().strip()
        topic_name = self.bulk_topic_combo.currentText().strip()
        file_path = self.bulk_file_input.text().strip()

        if not project_id:
            QMessageBox.warning(self, "Invalid Input", "Project ID is required.")
            return
        if not topic_name:
            QMessageBox.warning(self, "Invalid Input", "Topic name is required.")
            return

        if not file_path:
            QMessageBox.warning(self, "Invalid Input", "Select a messages file.")
            return
        if not Path(file_path).exists():
            QMessageBox.warning(self, "Invalid Input", "Selected file does not exist.")
            return

        try:
            json_path = self._get_auth_path()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Input", str(exc))
            return

        self.bulk_publish_btn.setEnabled(False)
        self.bulk_progress_counts = {"success": 0, "error": 0}
        self._set_bulk_status("Bulk publish started...")
        self.bulk_worker = BulkPublishWorker(
            project_id,
            topic_name,
            file_path,
            self.config.get("csv_delimiter", "auto"),
            json_path,
        )
        self.bulk_worker.log.connect(self._on_bulk_log)
        self.bulk_worker.summary.connect(self._on_bulk_summary)
        self.bulk_worker.error.connect(self._on_bulk_error)
        self.bulk_worker.finished.connect(self._on_bulk_finished)
        self.bulk_worker.start()

    def _on_bulk_log(self, status: str, message_id: str, error: str) -> None:
        self._add_log(status, message_id, error)
        if status == "SUCCESS":
            self.bulk_progress_counts["success"] += 1
        elif status == "ERROR":
            self.bulk_progress_counts["error"] += 1
        self._set_bulk_status(
            "Publishing... "
            f"Success: {self.bulk_progress_counts['success']}, Errors: {self.bulk_progress_counts['error']}"
        )

    def _on_bulk_summary(self, success_count: int, error_count: int) -> None:
        self._add_log(
            "SUMMARY",
            "",
            f"Bulk publish complete. Success: {success_count}, Errors: {error_count}",
        )
        self._set_bulk_status(f"Bulk publish complete. Success: {success_count}, Errors: {error_count}")

    def _on_bulk_error(self, error: str) -> None:
        self._set_bulk_status(f"Bulk publish failed: {error}")
        QMessageBox.warning(self, "Bulk Publish", error)

    def _on_bulk_finished(self) -> None:
        self.bulk_publish_btn.setEnabled(True)
        self.bulk_worker = None

    def _publish_message(self) -> None:
        try:
            payload = self._validate_inputs()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Input", str(exc))
            return

        self.publish_btn.setEnabled(False)
        self._set_publish_status("Publishing message...")
        self.worker = PublishWorker(
            payload["project_id"],
            payload["topic_name"],
            payload["message"],
            payload["attributes"],
            payload["json_path"],
        )
        self.worker.success.connect(self._on_publish_success)
        self.worker.error.connect(self._on_publish_error)
        self.worker.finished.connect(self._on_publish_finished)
        self.worker.start()

    def _on_publish_success(self, message_id: str) -> None:
        self._add_log("SUCCESS", message_id, "")
        self._set_publish_status(f"Published successfully (message id: {message_id})")

    def _on_publish_error(self, error: str) -> None:
        self._add_log("ERROR", "", error)
        self._set_publish_status(f"Publish failed: {error}")

    def _on_publish_finished(self) -> None:
        self.publish_btn.setEnabled(True)
        self.worker = None

    def _add_log(self, status: str, message_id: str, error: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = LogEntry(timestamp, status, message_id, error)
        self.logs.insert(0, entry)
        line = f"{entry.timestamp} | {entry.status} | {entry.message_id} | {entry.error}"
        for view in self.logs_views:
            view.insertItem(0, line)

    def _clear_all(self) -> None:
        self.message_input.clear()
        self.topic_combo.setCurrentText("")
        self.bulk_topic_combo.setCurrentText("")
        self.bulk_file_input.clear()
        for row in list(self.attribute_rows):
            self._remove_attribute_row(row)
        self.logs.clear()
        for view in self.logs_views:
            view.clear()
        self._set_publish_status("Idle")
        self._set_bulk_status("Idle")

    def _export_logs(self) -> None:
        if not self.logs:
            QMessageBox.information(self, "Export Logs", "No logs to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs to CSV",
            "pubsub_logs.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp", "status", "message_id", "error"])
            for entry in self.logs:
                writer.writerow(
                    [entry.timestamp, entry.status, entry.message_id, entry.error]
                )

        QMessageBox.information(self, "Export Logs", "CSV export complete.")

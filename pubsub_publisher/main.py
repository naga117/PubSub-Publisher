import sys
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

try:
    from pubsub_publisher import __version__
except Exception:  # pragma: no cover - fallback for atypical launcher contexts
    __version__ = "1.0.1"


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled_assets = Path(meipass) / "pubsub_publisher" / "assets"
            if bundled_assets.exists():
                return bundled_assets
    return Path(__file__).resolve().parent / "assets"


def _app_icon_path(assets_dir: Path) -> Path:
    if sys.platform == "darwin":
        macos_icon = assets_dir / "AppIcon.icns"
        if macos_icon.exists():
            return macos_icon
    return assets_dir / "icon.png"


def _should_set_runtime_icon() -> bool:
    # For bundled macOS apps, keep the Dock icon from Info.plist unchanged.
    return not (sys.platform == "darwin" and getattr(sys, "frozen", False))


class AnimatedSplashScreen(QWidget):
    def __init__(self, icon_path: Path) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self._base_message = "Starting application"
        self._dot_index = 0
        self._spinner_states = ["", ".", "..", "..."]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("splashCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(8)

        self.icon_label = QLabel(card)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_icon = QIcon(str(icon_path))
        icon_pixmap = app_icon.pixmap(84, 84)
        if not icon_pixmap.isNull():
            self.icon_label.setPixmap(icon_pixmap)
        card_layout.addWidget(self.icon_label)

        title = QLabel("PubSub Publisher", card)
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        self.status_label = QLabel("Starting application", card)
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)

        layout.addWidget(card)
        self.setStyleSheet(
            """
            #splashCard {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 12px;
            }
            QLabel#status {
                color: palette(dark);
            }
            """
        )

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick_status)
        self._tick_timer.start(140)

        self._icon_effect = QGraphicsOpacityEffect(self.icon_label)
        self.icon_label.setGraphicsEffect(self._icon_effect)
        self._icon_anim = QPropertyAnimation(self._icon_effect, b"opacity", self)
        self._icon_anim.setDuration(900)
        self._icon_anim.setStartValue(0.45)
        self._icon_anim.setEndValue(1.0)
        self._icon_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._icon_anim.setLoopCount(-1)
        self._icon_anim.start()

        self.adjustSize()
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        rect = screen.availableGeometry()
        self.move(
            rect.center().x() - self.width() // 2,
            rect.center().y() - self.height() // 2,
        )

    def _tick_status(self) -> None:
        suffix = self._spinner_states[self._dot_index % len(self._spinner_states)]
        self.status_label.setText(f"{self._base_message}{suffix}")
        self._dot_index += 1

    def set_status(self, message: str) -> None:
        self._base_message = message
        self.status_label.setText(message)
        QApplication.processEvents()

    def finish(self, window: QWidget) -> None:
        self._tick_timer.stop()
        self.hide()
        window.activateWindow()


def _set_native_macos_style(app: QApplication) -> None:
    for style_name in QStyleFactory.keys():
        if style_name.lower() in {"macos", "macintosh"}:
            app.setStyle(style_name)
            break


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PubSub Publisher")
    app.setApplicationVersion(__version__)
    _set_native_macos_style(app)
    assets_dir = _assets_dir()
    icon_path = _app_icon_path(assets_dir)
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        if not app_icon.isNull() and _should_set_runtime_icon():
            app.setWindowIcon(app_icon)

    splash = AnimatedSplashScreen(icon_path)
    splash.show()
    splash.raise_()
    splash.repaint()
    app.processEvents()

    def set_splash_status(message: str) -> None:
        splash.set_status(message)

    set_splash_status("Loading UI modules")
    from pubsub_publisher.ui_main import MainWindow

    set_splash_status("Building window")
    window = MainWindow()
    if _should_set_runtime_icon() and not app.windowIcon().isNull():
        window.setWindowIcon(app.windowIcon())
    set_splash_status("Ready")

    def open_main_window() -> None:
        splash.finish(window)
        window.show()
        window.activateWindow()

    # Keep splash visible briefly, then open the main window.
    QTimer.singleShot(1500, open_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

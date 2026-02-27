import sys
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QLabel,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled_assets = Path(meipass) / "pubsub_publisher" / "assets"
            if bundled_assets.exists():
                return bundled_assets
    return Path(__file__).resolve().parent / "assets"


class AnimatedSplashScreen(QWidget):
    def __init__(self, icon_path: Path, splash_path: Path) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self._base_message = "Starting application"
        self._dot_index = 0
        self._spinner_states = ["", ".", "..", "..."]

        self.setAutoFillBackground(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        if splash_path.exists():
            banner = QLabel()
            banner_pixmap = QPixmap(str(splash_path))
            if not banner_pixmap.isNull():
                banner.setPixmap(
                    banner_pixmap.scaled(
                        360,
                        120,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(banner)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_pixmap = QPixmap(str(icon_path))
        if not icon_pixmap.isNull():
            self.icon_label.setPixmap(
                icon_pixmap.scaled(
                    84,
                    84,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout.addWidget(self.icon_label)

        title = QLabel("PubSub Publisher")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel("Starting application")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

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
    _set_native_macos_style(app)
    assets_dir = _assets_dir()
    icon_path = assets_dir / "icon.png"
    splash_path = assets_dir / "splash.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    splash = AnimatedSplashScreen(icon_path, splash_path)
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
    set_splash_status("Opening window")
    window.show()
    set_splash_status("Ready")
    splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

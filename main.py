from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.styles import APP_STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("视频语音字幕帧定位器")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

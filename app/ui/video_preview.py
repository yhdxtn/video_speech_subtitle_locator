from __future__ import annotations

from pathlib import Path

import cv2
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class VideoPreview(QWidget):
    video_dropped = Signal(str)

    VIDEO_SUFFIXES = {
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".flv",
        ".wmv",
        ".m4v",
        ".ts",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._frame = None

        self.image_label = QLabel("拖入视频\n或点击右上角“选择视频”")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(620, 360)
        self.image_label.setObjectName("videoPreview")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)

    def show_frame(self, frame) -> None:
        self._frame = frame.copy() if frame is not None else None
        self._render_current_frame()

    def show_video_frame(self, video_path: str, frame_index: int = 0) -> bool:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(frame_index)))
            ok, frame = cap.read()
            if not ok:
                return False
            self.show_frame(frame)
            return True
        finally:
            cap.release()

    def clear(self) -> None:
        self._frame = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("拖入视频\n或点击右上角“选择视频”")

    def _render_current_frame(self) -> None:
        if self._frame is None:
            return
        rgb = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
        image = QImage(
            rgb.data,
            rgb.shape[1],
            rgb.shape[0],
            rgb.strides[0],
            QImage.Format_RGB888,
        ).copy()
        pixmap = QPixmap.fromImage(image)
        self.image_label.setPixmap(
            pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self.image_label.setText("")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._render_current_frame()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            if Path(urls[0].toLocalFile()).suffix.lower() in self.VIDEO_SUFFIXES:
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.video_dropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()

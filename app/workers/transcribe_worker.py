from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal

from app.config import TranscribeConfig
from app.models.subtitle_event import SubtitleEvent
from app.services.transcription_pipeline import TranscriptionPipeline


class TranscribeWorker(QThread):
    progress_changed = Signal(int)
    subtitle_found = Signal(object, int)
    status_changed = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        video_path: str,
        config: TranscribeConfig,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.video_path = video_path
        self.config = config
        self.pipeline = TranscriptionPipeline(config)

    def run(self) -> None:
        try:
            events: list[SubtitleEvent] = self.pipeline.run(
                self.video_path,
                progress_callback=self.progress_changed.emit,
                event_callback=self.subtitle_found.emit,
                status_callback=self.status_changed.emit,
            )
            self.completed.emit(events)
        except Exception as exc:  # noqa: BLE001
            details = traceback.format_exc()
            self.failed.emit(f"{exc}\n\n详细错误：\n{details}")

    def request_stop(self) -> None:
        self.pipeline.stop()

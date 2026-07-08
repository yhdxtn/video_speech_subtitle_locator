from __future__ import annotations

import re
from pathlib import Path

import cv2

from app.models.subtitle_event import SubtitleEvent
from app.utils.time_utils import format_clock


class ScreenshotService:
    INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')

    def __init__(self, video_path: str, output_dir: str) -> None:
        self.video_path = video_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开视频用于截图：{video_path}")

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()

    @classmethod
    def _safe_text(cls, text: str, max_length: int = 28) -> str:
        value = cls.INVALID_FILENAME.sub("_", text.strip())
        value = re.sub(r"\s+", " ", value).strip(" ._")
        return (value[:max_length] or "subtitle").strip()

    def save_start_frame(self, event: SubtitleEvent, sequence: int) -> str:
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, event.start_frame_index)
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError(
                f"无法读取第 {event.start_frame_number} 帧，截图保存失败。"
            )

        timestamp = format_clock(event.start_seconds).replace(":", "-").replace(".", "-")
        text = self._safe_text(event.text)
        filename = (
            f"{sequence:04d}_frame_{event.start_frame_number:08d}_"
            f"{timestamp}_{text}.jpg"
        )
        path = self.output_dir / filename

        # imencode + tofile 支持 Windows 中文路径。
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not ok:
            raise RuntimeError("JPEG 编码失败。")
        encoded.tofile(str(path))
        return str(path)

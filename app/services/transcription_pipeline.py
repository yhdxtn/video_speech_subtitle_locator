from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Optional

from app.config import TranscribeConfig
from app.models.subtitle_event import SubtitleEvent
from app.services.screenshot_service import ScreenshotService
from app.services.speech_service import SpeechService
from app.services.video_service import VideoService

ProgressCallback = Callable[[int], None]
EventCallback = Callable[[SubtitleEvent, int], None]
StatusCallback = Callable[[str], None]


class TranscriptionPipeline:
    def __init__(self, config: TranscribeConfig) -> None:
        config.validate()
        self.config = config
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(
        self,
        video_path: str,
        progress_callback: Optional[ProgressCallback] = None,
        event_callback: Optional[EventCallback] = None,
        status_callback: Optional[StatusCallback] = None,
    ) -> list[SubtitleEvent]:
        self._stop_event.clear()
        path = Path(video_path)
        if not path.is_file():
            raise FileNotFoundError(f"视频不存在：{path}")

        info = VideoService.read_info(str(path))
        speech = SpeechService(self.config, status_callback=status_callback)
        segments, transcribe_info = speech.transcribe(str(path))
        audio_duration = float(
            getattr(transcribe_info, "duration", 0.0) or info.duration_seconds
        )

        screenshot_service: ScreenshotService | None = None
        if self.config.create_screenshots:
            screenshot_service = ScreenshotService(
                str(path),
                self.config.screenshot_dir,
            )

        events: list[SubtitleEvent] = []
        try:
            for segment in segments:
                if self._stop_event.is_set():
                    break

                text = str(getattr(segment, "text", "")).strip()
                if not text:
                    continue

                start_seconds, end_seconds = speech.segment_timing(segment)
                start_seconds = max(0.0, start_seconds)
                end_seconds = max(start_seconds, end_seconds)
                start_frame_index = VideoService.time_to_start_frame_index(
                    start_seconds,
                    info.fps,
                    info.total_frames,
                )
                end_frame_index = VideoService.time_to_end_frame_index(
                    end_seconds,
                    info.fps,
                    info.total_frames,
                )

                event = SubtitleEvent(
                    text=text,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    start_frame_index=start_frame_index,
                    end_frame_index=end_frame_index,
                    fps=info.fps,
                    confidence=speech.segment_confidence(segment),
                )

                sequence = len(events) + 1
                if screenshot_service is not None:
                    try:
                        event.screenshot_path = screenshot_service.save_start_frame(
                            event,
                            sequence,
                        )
                    except Exception as exc:  # noqa: BLE001
                        event.screenshot_path = None
                        if status_callback is not None:
                            status_callback(
                                f"第 {sequence} 条字幕已识别，但截图失败：{exc}"
                            )

                events.append(event)
                if event_callback is not None:
                    event_callback(event, sequence)

                if progress_callback is not None:
                    denominator = max(audio_duration, 0.001)
                    progress = int(min(99.0, end_seconds / denominator * 100.0))
                    progress_callback(progress)

            if progress_callback is not None:
                progress_callback(100 if not self._stop_event.is_set() else 0)
            if status_callback is not None:
                if self._stop_event.is_set():
                    status_callback(f"已停止；保留已识别的 {len(events)} 条字幕。")
                else:
                    language = getattr(transcribe_info, "language", "") or "未知"
                    status_callback(
                        f"识别完成：{len(events)} 条字幕；检测语言 {language}。"
                    )
            return events
        finally:
            if screenshot_service is not None:
                screenshot_service.close()

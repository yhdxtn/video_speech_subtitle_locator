from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from app.models.subtitle_event import SubtitleEvent
from app.utils.time_utils import format_clock, format_srt_timestamp


class ExportService:
    @staticmethod
    def export_csv(path: str, events: Iterable[SubtitleEvent]) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "序号",
                    "字幕",
                    "开始时间",
                    "结束时间",
                    "首次帧号(1-based)",
                    "帧索引(0-based)",
                    "结束帧号(1-based)",
                    "视频FPS",
                    "置信度",
                    "截图路径",
                ]
            )
            for index, event in enumerate(events, start=1):
                writer.writerow(
                    [
                        index,
                        event.text,
                        format_clock(event.start_seconds),
                        format_clock(event.end_seconds),
                        event.start_frame_number,
                        event.start_frame_index,
                        event.end_frame_number,
                        f"{event.fps:.6f}",
                        f"{event.confidence:.4f}",
                        event.screenshot_path or "",
                    ]
                )

    @staticmethod
    def export_srt(path: str, events: Iterable[SubtitleEvent]) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for index, event in enumerate(events, start=1):
            lines.extend(
                [
                    str(index),
                    f"{format_srt_timestamp(event.start_seconds)} --> "
                    f"{format_srt_timestamp(event.end_seconds)}",
                    event.text,
                    "",
                ]
            )
        output.write_text("\n".join(lines), encoding="utf-8-sig")

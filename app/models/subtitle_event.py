from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class SubtitleEvent:
    text: str
    start_seconds: float
    end_seconds: float
    start_frame_index: int
    end_frame_index: int
    fps: float
    confidence: float = 0.0
    screenshot_path: Optional[str] = None

    @property
    def start_frame_number(self) -> int:
        return self.start_frame_index + 1

    @property
    def end_frame_number(self) -> int:
        return self.end_frame_index + 1

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VideoInfo:
    fps: float
    total_frames: int
    width: int
    height: int

    @property
    def duration_seconds(self) -> float:
        if self.fps <= 0:
            return 0.0
        return self.total_frames / self.fps

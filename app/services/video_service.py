from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from app.models.video_info import VideoInfo


class VideoService:
    @staticmethod
    def read_info(video_path: str) -> VideoInfo:
        path = Path(video_path)
        if not path.is_file():
            raise FileNotFoundError(f"视频不存在：{path}")

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频：{path}")
        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        finally:
            cap.release()

        if not np.isfinite(fps) or fps <= 0:
            raise RuntimeError("无法读取有效的视频 FPS。")
        if total_frames <= 0:
            raise RuntimeError("无法读取有效的视频总帧数。")
        return VideoInfo(
            fps=fps,
            total_frames=total_frames,
            width=width,
            height=height,
        )

    @staticmethod
    def time_to_start_frame_index(
        seconds: float,
        fps: float,
        total_frames: int,
    ) -> int:
        # 第一张时间戳不早于字幕开始时间的帧。
        index = int(math.ceil(max(0.0, seconds) * fps - 1e-9))
        return max(0, min(total_frames - 1, index))

    @staticmethod
    def time_to_end_frame_index(
        seconds: float,
        fps: float,
        total_frames: int,
    ) -> int:
        index = int(math.floor(max(0.0, seconds) * fps))
        return max(0, min(total_frames - 1, index))

    @staticmethod
    def read_frame(video_path: str, frame_index: int):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            ok, frame = cap.read()
            return frame if ok else None
        finally:
            cap.release()

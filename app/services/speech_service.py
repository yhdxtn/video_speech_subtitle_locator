from __future__ import annotations

import json
import re
import subprocess
import tempfile
from difflib import SequenceMatcher
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterator

import imageio_ffmpeg
from opencc import OpenCC

from app.config import TranscribeConfig

StatusCallback = Callable[[str], None]
SIMPLIFIER = OpenCC("t2s")


class SpeechService:
    """Speech-to-text wrapper used by the worker thread.

    Uses open-source Whisper ONNX models through Transformers.js/WebAssembly.
    This avoids the Python native DLLs blocked by the local Windows application
    control policy while still giving much better accuracy than the built-in
    Windows dictation recognizer.
    """

    def __init__(
        self,
        config: TranscribeConfig,
        status_callback: StatusCallback | None = None,
    ) -> None:
        self.config = config
        self.status_callback = status_callback

    def _status(self, text: str) -> None:
        if self.status_callback is not None:
            self.status_callback(text)

    def transcribe(self, media_path: str) -> tuple[Iterator[Any], Any]:
        self._status("正在提取视频音轨...")
        wav_path = self._extract_wav(media_path)
        try:
            self._status(f"正在使用开源 Whisper 模型 {self.config.model_name} 生成字幕...")
            segments = self._recognize_with_transformers_js(wav_path)
        finally:
            try:
                wav_path.unlink(missing_ok=True)
            except OSError:
                pass

        duration = max((segment.end for segment in segments), default=0.0)
        info = SimpleNamespace(duration=duration, language=self.config.language or "zh")
        return iter(segments), info

    @staticmethod
    def _extract_wav(media_path: str) -> Path:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        command = [
            ffmpeg,
            "-y",
            "-i",
            media_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            str(wav_path),
        ]
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if completed.returncode != 0:
            try:
                wav_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise RuntimeError("ffmpeg 音频提取失败：\n" + completed.stderr.strip())
        return wav_path

    def _recognize_with_transformers_js(self, wav_path: Path) -> list[Any]:
        script = Path(__file__).with_name("transformers_whisper_asr.mjs")
        model = self._model_id(self.config.model_name)
        completed = subprocess.run(
            [
                "node",
                str(script),
                str(wav_path),
                model,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "开源 Whisper 识别失败：\n" + completed.stderr.strip()
            )

        raw = completed.stdout.strip()
        if not raw:
            return []
        payload = json.loads(raw)
        if isinstance(payload, dict):
            payload = [payload]

        segments: list[Any] = []
        for item in payload:
            text = SIMPLIFIER.convert(str(item.get("text", "")).strip())
            if not text:
                continue
            start = float(item.get("start", 0.0) or 0.0)
            end = float(item.get("end", start) or start)
            confidence = float(item.get("confidence", 0.0) or 0.0)
            segments.append(
                SimpleNamespace(
                    text=text,
                    start=start,
                    end=max(start, end),
                    words=[
                        SimpleNamespace(
                            start=start,
                            end=max(start, end),
                            probability=confidence,
                        )
                    ],
                )
            )
        return self._merge_repeated_segments(segments)

    @staticmethod
    def _model_id(name: str) -> str:
        normalized = name.strip()
        if "/" in normalized:
            return normalized
        mapping = {
            "base": "onnx-community/whisper-base",
            "small": "onnx-community/whisper-small",
        }
        return mapping.get(normalized, "onnx-community/whisper-base")

    @classmethod
    def _merge_repeated_segments(cls, segments: list[Any]) -> list[Any]:
        merged: list[Any] = []
        for segment in sorted(segments, key=lambda item: (item.start, item.end)):
            segment.text = cls._collapse_repeated_text(str(segment.text).strip())
            if not segment.text:
                continue

            if merged and cls._is_repeat(merged[-1], segment):
                previous = merged[-1]
                if len(cls._normalize_text(segment.text)) > len(
                    cls._normalize_text(previous.text)
                ):
                    previous.text = segment.text
                previous.end = max(previous.end, segment.end)
                previous.words = [
                    SimpleNamespace(
                        start=previous.start,
                        end=previous.end,
                        probability=max(
                            cls.segment_confidence(previous),
                            cls.segment_confidence(segment),
                        ),
                    )
                ]
                continue

            merged.append(segment)
        return merged

    @classmethod
    def _is_repeat(cls, previous: Any, current: Any) -> bool:
        gap = float(current.start) - float(previous.end)
        if gap > 2.5:
            return False

        left = cls._normalize_text(str(previous.text))
        right = cls._normalize_text(str(current.text))
        if not left or not right:
            return False
        if left == right:
            return True

        shorter = min(len(left), len(right))
        if shorter < 3:
            return False
        if left in right or right in left:
            return True

        if shorter < 4:
            return False
        return SequenceMatcher(None, left, right).ratio() >= 0.92

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"[^0-9a-zA-Z\u3400-\u4dbf\u4e00-\u9fff]+", "", text).lower()

    @classmethod
    def _collapse_repeated_text(cls, text: str) -> str:
        normalized = cls._normalize_text(text)
        if not normalized:
            return ""

        for unit_length in range(2, max(2, len(normalized) // 2) + 1):
            unit = normalized[:unit_length]
            repeats = len(normalized) // unit_length
            if repeats < 2:
                continue
            repeated = unit * repeats
            remainder = normalized[len(repeated) :]
            if normalized == repeated + remainder and len(remainder) < unit_length:
                return text[:unit_length]
        return text

    @staticmethod
    def segment_timing(segment: Any) -> tuple[float, float]:
        words = list(getattr(segment, "words", None) or [])
        timed_words = [
            word
            for word in words
            if getattr(word, "start", None) is not None
            and getattr(word, "end", None) is not None
        ]
        if timed_words:
            return float(timed_words[0].start), float(timed_words[-1].end)
        return float(segment.start), float(segment.end)

    @staticmethod
    def segment_confidence(segment: Any) -> float:
        words = list(getattr(segment, "words", None) or [])
        values = [
            float(word.probability)
            for word in words
            if getattr(word, "probability", None) is not None
        ]
        if not values:
            return 0.0
        return max(0.0, min(1.0, sum(values) / len(values)))

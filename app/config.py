from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TranscribeConfig:
    model_name: str = "small"
    language: str | None = "zh"
    beam_size: int = 5
    vad_filter: bool = False
    create_screenshots: bool = True
    screenshot_dir: str = ""

    def validate(self) -> None:
        if not self.model_name.strip():
            raise ValueError("语音识别模型不能为空。")
        if self.language is not None and not self.language.strip():
            raise ValueError("语言代码不能为空字符串；自动检测请使用 None。")
        if not 1 <= self.beam_size <= 10:
            raise ValueError("Beam size 必须位于 1 到 10 之间。")
        if self.create_screenshots:
            if not self.screenshot_dir.strip():
                raise ValueError("启用截图后必须设置截图保存目录。")
            Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)

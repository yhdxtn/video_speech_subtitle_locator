from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import TranscribeConfig
from app.models.subtitle_event import SubtitleEvent
from app.models.video_info import VideoInfo
from app.services.export_service import ExportService
from app.services.video_service import VideoService
from app.ui.video_preview import VideoPreview
from app.utils.time_utils import format_clock
from app.workers.transcribe_worker import TranscribeWorker


class MainWindow(QMainWindow):
    LANGUAGE_OPTIONS = {
        "自动检测": None,
        "中文": "zh",
        "英文": "en",
        "日语": "ja",
        "韩语": "ko",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("视频语音字幕帧定位器")
        self.resize(1580, 950)

        self.video_path = ""
        self.video_info: VideoInfo | None = None
        self.events: list[SubtitleEvent] = []
        self.worker: TranscribeWorker | None = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(12)

        title = QLabel("视频语音字幕帧定位器")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "从视频音轨识别语音并生成字幕，同时定位每条字幕开始时间对应的视频帧；截图可选。"
        )
        subtitle.setObjectName("subtitleLabel")
        root.addWidget(title)
        root.addWidget(subtitle)

        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择或拖入 MP4 / MKV / AVI / MOV 视频")
        self.choose_button = QPushButton("选择视频")
        self.choose_button.setObjectName("primaryButton")
        file_row.addWidget(self.path_edit, 1)
        file_row.addWidget(self.choose_button)
        root.addLayout(file_row)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 3)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        self.preview = VideoPreview()
        left_layout.addWidget(self.preview, 1)

        metrics = QHBoxLayout()
        self.fps_value = self._metric("FPS", "--", metrics)
        self.frames_value = self._metric("总帧数", "--", metrics)
        self.duration_value = self._metric("时长", "--", metrics)
        self.resolution_value = self._metric("分辨率", "--", metrics)
        left_layout.addLayout(metrics)

        self.preview_info_label = QLabel("点击下方字幕行，会预览该字幕开始时间对应的帧。")
        self.preview_info_label.setObjectName("mutedLabel")
        left_layout.addWidget(self.preview_info_label)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)

        recognize_group = QGroupBox("语音识别参数")
        recognize_form = QFormLayout(recognize_group)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["base", "small"])
        self.model_combo.setCurrentText("base")
        self.model_combo.setEnabled(True)
        recognize_form.addRow("Whisper 模型", self.model_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItems(list(self.LANGUAGE_OPTIONS.keys()))
        self.language_combo.setCurrentText("中文")
        recognize_form.addRow("语音语言", self.language_combo)

        self.beam_spin = QSpinBox()
        self.beam_spin.setRange(1, 10)
        self.beam_spin.setValue(5)
        self.beam_spin.setEnabled(False)
        recognize_form.addRow("Beam size", self.beam_spin)

        self.vad_checkbox = QCheckBox("过滤长时间无语音区域")
        self.vad_checkbox.setChecked(False)
        self.vad_checkbox.setEnabled(False)
        recognize_form.addRow("VAD", self.vad_checkbox)
        right_layout.addWidget(recognize_group)

        screenshot_group = QGroupBox("截图")
        screenshot_layout = QVBoxLayout(screenshot_group)
        self.screenshot_checkbox = QCheckBox("识别时保存每条字幕开始对应的那一帧")
        self.screenshot_checkbox.setChecked(True)
        screenshot_layout.addWidget(self.screenshot_checkbox)

        screenshot_row = QHBoxLayout()
        self.screenshot_dir_edit = QLineEdit()
        self.screenshot_dir_edit.setPlaceholderText("截图保存目录")
        self.choose_screenshot_dir_button = QPushButton("选择目录")
        screenshot_row.addWidget(self.screenshot_dir_edit, 1)
        screenshot_row.addWidget(self.choose_screenshot_dir_button)
        screenshot_layout.addLayout(screenshot_row)

        screenshot_note = QLabel(
            "关闭上方勾选后，只生成字幕、时间和帧号，不读取或保存截图。"
        )
        screenshot_note.setWordWrap(True)
        screenshot_note.setObjectName("mutedLabel")
        screenshot_layout.addWidget(screenshot_note)
        right_layout.addWidget(screenshot_group)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("开始语音转字幕")
        self.start_button.setObjectName("primaryButton")
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.setEnabled(False)
        button_row.addWidget(self.start_button, 1)
        button_row.addWidget(self.stop_button)
        right_layout.addLayout(button_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        right_layout.addWidget(self.progress)

        self.status_label = QLabel("请选择视频")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("mutedLabel")
        right_layout.addWidget(self.status_label)

        export_group = QGroupBox("导出")
        export_layout = QHBoxLayout(export_group)
        self.export_csv_button = QPushButton("导出 CSV")
        self.export_srt_button = QPushButton("导出 SRT")
        self.export_csv_button.setEnabled(False)
        self.export_srt_button.setEnabled(False)
        export_layout.addWidget(self.export_csv_button)
        export_layout.addWidget(self.export_srt_button)
        right_layout.addWidget(export_group)
        right_layout.addStretch()

        note = QLabel(
            "定位逻辑：语音识别得到字幕开始时间 → 根据视频 FPS 换算首帧索引 → 可选保存该帧截图。\n"
            "帧号从 1 开始；帧索引从 0 开始。"
        )
        note.setWordWrap(True)
        note.setObjectName("mutedLabel")
        right_layout.addWidget(note)
        splitter.addWidget(right_panel)
        splitter.setSizes([1030, 430])

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "序号",
                "字幕",
                "开始时间",
                "结束时间",
                "首次帧号",
                "帧索引",
                "FPS",
                "置信度",
                "截图",
                "截图文件",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        widths = [56, 460, 125, 125, 95, 90, 90, 85, 70, 360]
        for index, width in enumerate(widths):
            self.table.setColumnWidth(index, width)
        root.addWidget(self.table, 2)

    @staticmethod
    def _metric(title: str, initial: str, parent_layout: QHBoxLayout) -> QLabel:
        box = QVBoxLayout()
        name = QLabel(title)
        name.setObjectName("mutedLabel")
        value = QLabel(initial)
        value.setObjectName("metricValue")
        box.addWidget(name)
        box.addWidget(value)
        parent_layout.addLayout(box)
        parent_layout.addStretch()
        return value

    def _connect_signals(self) -> None:
        self.choose_button.clicked.connect(self.choose_video)
        self.preview.video_dropped.connect(self.load_video)
        self.path_edit.editingFinished.connect(self.load_path_from_edit)
        self.choose_screenshot_dir_button.clicked.connect(self.choose_screenshot_dir)
        self.screenshot_checkbox.toggled.connect(self.toggle_screenshot_controls)
        self.start_button.clicked.connect(self.start_transcription)
        self.stop_button.clicked.connect(self.stop_transcription)
        self.export_csv_button.clicked.connect(self.export_csv)
        self.export_srt_button.clicked.connect(self.export_srt)
        self.table.itemSelectionChanged.connect(self.preview_selected_subtitle)

    def choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频",
            "",
            "视频文件 (*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.m4v *.ts);;所有文件 (*)",
        )
        if path:
            self.load_video(path)

    def load_path_from_edit(self) -> None:
        path = self.path_edit.text().strip()
        if path and path != self.video_path and Path(path).is_file():
            self.load_video(path)

    def load_video(self, path: str) -> None:
        try:
            info = VideoService.read_info(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "无法打开视频", str(exc))
            return

        self.video_path = str(Path(path).resolve())
        self.video_info = info
        self.path_edit.setText(self.video_path)
        self.events = []
        self.table.setRowCount(0)
        self.progress.setValue(0)
        self.export_csv_button.setEnabled(False)
        self.export_srt_button.setEnabled(False)

        self.preview.show_video_frame(self.video_path, 0)
        self.fps_value.setText(f"{info.fps:.3f}")
        self.frames_value.setText(str(info.total_frames))
        self.duration_value.setText(format_clock(info.duration_seconds))
        self.resolution_value.setText(f"{info.width} × {info.height}")
        self.preview_info_label.setText("当前预览：第 1 帧 / 帧索引 0 / 00:00:00.000")

        default_screenshot_dir = Path(self.video_path).with_suffix("")
        self.screenshot_dir_edit.setText(f"{default_screenshot_dir}_screenshots")
        self.status_label.setText("视频已加载。点击“开始语音转字幕”。")

    def choose_screenshot_dir(self) -> None:
        initial = self.screenshot_dir_edit.text().strip() or str(Path.cwd())
        path = QFileDialog.getExistingDirectory(self, "选择截图保存目录", initial)
        if path:
            self.screenshot_dir_edit.setText(path)

    def toggle_screenshot_controls(self, checked: bool) -> None:
        self.screenshot_dir_edit.setEnabled(checked)
        self.choose_screenshot_dir_button.setEnabled(checked)

    def _build_config(self) -> TranscribeConfig:
        language = self.LANGUAGE_OPTIONS[self.language_combo.currentText()]
        config = TranscribeConfig(
            model_name=self.model_combo.currentText(),
            language=language,
            beam_size=self.beam_spin.value(),
            vad_filter=self.vad_checkbox.isChecked(),
            create_screenshots=self.screenshot_checkbox.isChecked(),
            screenshot_dir=self.screenshot_dir_edit.text().strip(),
        )
        config.validate()
        return config

    def start_transcription(self) -> None:
        if not self.video_path:
            QMessageBox.warning(self, "未选择视频", "请先选择视频。")
            return
        if self.worker is not None and self.worker.isRunning():
            return

        try:
            config = self._build_config()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "参数错误", str(exc))
            return

        self.events = []
        self.table.setRowCount(0)
        self.progress.setValue(0)
        self.export_csv_button.setEnabled(False)
        self.export_srt_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("正在启动语音识别……")

        self.worker = TranscribeWorker(self.video_path, config, self)
        self.worker.progress_changed.connect(self.progress.setValue)
        self.worker.subtitle_found.connect(self.add_subtitle_event)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.completed.connect(self.transcription_completed)
        self.worker.failed.connect(self.transcription_failed)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def stop_transcription(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.status_label.setText("正在停止；当前语音识别段结束后退出……")
            self.worker.request_stop()
            self.stop_button.setEnabled(False)

    def add_subtitle_event(self, event: SubtitleEvent, sequence: int) -> None:
        self.events.append(event)
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [
            str(sequence),
            event.text,
            format_clock(event.start_seconds),
            format_clock(event.end_seconds),
            str(event.start_frame_number),
            str(event.start_frame_index),
            f"{event.fps:.3f}",
            f"{event.confidence:.3f}",
            "是" if event.screenshot_path else "否",
            event.screenshot_path or "",
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column in {0, 2, 3, 4, 5, 6, 7, 8}:
                item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, column, item)
        self.table.scrollToBottom()

    def transcription_completed(self, events: object) -> None:
        self.events = list(events)
        enabled = bool(self.events)
        self.export_csv_button.setEnabled(enabled)
        self.export_srt_button.setEnabled(enabled)
        if self.events:
            self.table.selectRow(0)

    def transcription_failed(self, message: str) -> None:
        self.status_label.setText("语音识别失败")
        QMessageBox.critical(self, "识别失败", message)

    def worker_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def preview_selected_subtitle(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows or not self.video_path:
            return
        row = rows[0].row()
        if not 0 <= row < len(self.events):
            return
        event = self.events[row]
        if self.preview.show_video_frame(self.video_path, event.start_frame_index):
            self.preview_info_label.setText(
                f"当前预览：第 {event.start_frame_number} 帧 / "
                f"帧索引 {event.start_frame_index} / "
                f"{format_clock(event.start_seconds)} / 字幕：{event.text}"
            )

    def export_csv(self) -> None:
        if not self.events:
            return
        default = str(Path(self.video_path).with_suffix("")) + "_字幕帧.csv"
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", default, "CSV (*.csv)")
        if path:
            ExportService.export_csv(path, self.events)
            self.status_label.setText(f"CSV 已导出：{path}")

    def export_srt(self) -> None:
        if not self.events:
            return
        default = str(Path(self.video_path).with_suffix("")) + ".srt"
        path, _ = QFileDialog.getSaveFileName(self, "导出 SRT", default, "SRT (*.srt)")
        if path:
            ExportService.export_srt(path, self.events)
            self.status_label.setText(f"SRT 已导出：{path}")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(3000)
        super().closeEvent(event)

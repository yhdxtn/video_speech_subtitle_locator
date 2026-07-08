# 视频语音字幕帧定位器

这是一个 PySide6 图形客户端。它**不再 OCR 识别画面文字**，而是直接读取视频音轨，通过 faster-whisper 把语音转成字幕，并把每条字幕的开始时间换算成对应的视频帧。

截图功能可开关：

- 勾选“识别时保存每条字幕开始对应的那一帧”：生成字幕 + 帧号 + 截图。
- 取消勾选：只生成字幕 + 时间 + 帧号，不截图。

## 处理流程

```text
视频文件
   ↓
读取音轨 / 语音识别
   ↓
faster-whisper 生成字幕和时间戳
   ↓
字幕开始时间 × 视频 FPS
   ↓
换算首次对应帧索引
   ↓
可选：读取该帧并保存 JPG
```

## 项目结构

```text
video_speech_subtitle_locator/
├─ main.py
├─ requirements.txt
├─ install_windows_cpu.bat
├─ run.bat
├─ README.md
└─ app/
   ├─ config.py
   ├─ models/
   │  ├─ subtitle_event.py
   │  └─ video_info.py
   ├─ services/
   │  ├─ speech_service.py
   │  ├─ video_service.py
   │  ├─ screenshot_service.py
   │  ├─ transcription_pipeline.py
   │  └─ export_service.py
   ├─ workers/
   │  └─ transcribe_worker.py
   ├─ ui/
   │  ├─ main_window.py
   │  ├─ video_preview.py
   │  └─ styles.py
   └─ utils/
      └─ time_utils.py
```

## Windows 使用

推荐 Python 3.10、3.11 或 3.12。

1. 解压项目。
2. 双击 `install_windows_cpu.bat`。
3. 安装完成后双击 `run.bat`。
4. 选择视频。
5. 选择语音语言和 Whisper 模型。
6. 根据需要勾选或取消“保存截图”。
7. 点击“开始语音转字幕”。
8. 点击结果表的一行，左侧预览该字幕开始时间对应的视频帧。
9. 可导出 CSV 或 SRT。

## 字幕与帧号的关系

软件优先使用 faster-whisper 返回的单词级时间戳来确定每个字幕段的真实开始时间。

对字幕开始时间 `t` 和视频帧率 `fps`：

```text
frame_index = ceil(t × fps)
frame_number = frame_index + 1
```

这里选择的是“时间戳不早于字幕开始时间的第一帧”。

例如：

```text
字幕开始时间：4.960 秒
FPS：25
4.960 × 25 = 124
帧索引：124
人类习惯帧号：125
```

## 截图

启用截图后，每条字幕保存一张 JPG。截图是视频原始帧，不叠加程序生成的字幕文字。

默认目录：

```text
原视频名_screenshots/
```

示例文件名：

```text
0001_frame_00000125_00-00-04-960_你好请问有人吗.jpg
```

## 模型

默认 `small`，CPU 使用 `int8`。

首次使用某个模型时会下载模型到：

```text
models_cache/
```

之后可复用本地缓存。

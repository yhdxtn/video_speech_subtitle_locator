from __future__ import annotations

import math


def format_clock(seconds: float, decimal_digits: int = 3) -> str:
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole_seconds = int(seconds % 60)
    fraction_scale = 10**decimal_digits
    fraction = int(round((seconds - math.floor(seconds)) * fraction_scale))
    if fraction >= fraction_scale:
        whole_seconds += 1
        fraction = 0
    if whole_seconds >= 60:
        minutes += 1
        whole_seconds = 0
    if minutes >= 60:
        hours += 1
        minutes = 0
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{fraction:0{decimal_digits}d}"


def format_srt_timestamp(seconds: float) -> str:
    return format_clock(seconds, 3).replace(".", ",")

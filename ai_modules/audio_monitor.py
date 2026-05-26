"""
Basic audio monitoring — detects if sustained sound is present.
Uses pyaudio to sample the microphone; returns RMS level.
Frontend also does basic audio monitoring via Web Audio API.
This module is used server-side for supplemental checks.
"""

import threading
import time
from config import AUDIO_THRESHOLD

# ── State ──────────────────────────────────────────────────────────────────────
_monitoring   = False
_monitor_thread = None
_alert_callback = None
_current_rms  = 0

def _compute_rms(audio_data):
    """Compute Root Mean Square of audio samples."""
    import struct
    import math
    count  = len(audio_data) // 2
    shorts = struct.unpack(f"{count}h", audio_data)
    sum_sq = sum(s * s for s in shorts)
    return math.sqrt(sum_sq / count) if count > 0 else 0

def analyze_audio_level(rms_value):
    """
    Given an RMS value (from frontend or backend),
    return whether it exceeds the suspicious threshold.
    """
    return {
        "rms":         rms_value,
        "is_loud":     rms_value > AUDIO_THRESHOLD,
        "flags":       ["AUDIO_DETECTED"] if rms_value > AUDIO_THRESHOLD else []
    }
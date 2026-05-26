"""
YOLOv8-based object detection — specifically detects mobile phones.
Uses ultralytics YOLOv8n (nano) for speed on CPU.
"""

import base64
import numpy as np
import cv2
from ultralytics import YOLO
import os

# ── Load model once ────────────────────────────────────────────────────────────
# YOLOv8n auto-downloads on first run to ~/.cache/ultralytics/
_model = None

# COCO class IDs we care about
PHONE_CLASS_ID  = 67   # 'cell phone' in COCO dataset
PERSON_CLASS_ID = 0    # 'person'

DETECT_CLASSES = {
    PHONE_CLASS_ID:  "cell_phone",
    PERSON_CLASS_ID: "person",
}

def _get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")  # downloads automatically first time
    return _model

def decode_frame(b64_string):
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    np_arr    = np.frombuffer(img_bytes, np.uint8)
    frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame

def detect_objects(b64_frame):
    """
    Run YOLOv8 on a frame. Return detected suspicious objects.

    Returns dict:
    {
        "phone_detected":   bool,
        "detections":       [{"label": str, "confidence": float}, ...]
        "flags":            [str, ...]
    }
    """
    result = {
        "phone_detected": False,
        "detections":     [],
        "flags":          []
    }

    try:
        frame = decode_frame(b64_frame)
        if frame is None:
            return result

        model   = _get_model()
        # Run inference; only look for phone and person classes
        outputs = model(
            frame,
            classes=list(DETECT_CLASSES.keys()),
            conf=0.4,       # 40% confidence threshold
            verbose=False
        )

        for detection in outputs[0].boxes:
            cls_id     = int(detection.cls[0])
            confidence = float(detection.conf[0])
            label      = DETECT_CLASSES.get(cls_id, "unknown")

            result["detections"].append({
                "label":      label,
                "confidence": round(confidence, 3)
            })

            if cls_id == PHONE_CLASS_ID:
                result["phone_detected"] = True
                result["flags"].append("MOBILE_DETECTED")

    except Exception as e:
        result["flags"].append(f"YOLO_ERROR: {str(e)}")

    return result
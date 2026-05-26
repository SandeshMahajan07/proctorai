"""
Face detection + 68-point landmark head pose estimation.
Uses opencv-contrib (cv2.face.FacemarkLBF) — works on Python 3.13, no mediapipe/dlib.
"""

import cv2
import numpy as np
import base64
from collections import deque
from config import HEAD_POSE_YAW_THRESH, HEAD_POSE_PITCH_THRESH
import os

_BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
_LBFMODEL      = os.path.join(_BASE_DIR, "lbfmodel.yaml")

# ── Detectors (lazy init) ──────────────────────────────────────────────────────
_cascade  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_facemark = None

def _get_facemark():
    global _facemark
    if _facemark is None:
        fm = cv2.face.createFacemarkLBF()
        fm.loadModel(_LBFMODEL)
        _facemark = fm
    return _facemark

# ── Multi-face consistency buffer (3 frames) ───────────────────────────────────
_face_count_buffer = deque(maxlen=3)

# ── 3D model points for solvePnP head pose ────────────────────────────────────
MODEL_POINTS = np.array([
    (0.0,    0.0,     0.0),    # Nose tip          — landmark 30
    (0.0,   -330.0, -65.0),    # Chin              — landmark 8
    (-225.0,  170.0, -135.0),  # Left eye corner   — landmark 45
    ( 225.0,  170.0, -135.0),  # Right eye corner  — landmark 36
    (-150.0, -150.0, -125.0),  # Left mouth corner — landmark 54
    ( 150.0, -150.0, -125.0),  # Right mouth corner— landmark 48
], dtype=np.float64)

# Corresponding LBF landmark indices
LANDMARK_IDX = [30, 8, 45, 36, 54, 48]


def decode_frame(b64_string):
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    np_arr    = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


def get_head_pose(landmarks, frame_shape):
    h, w = frame_shape[:2]
    image_points = np.array(
        [(landmarks[i][0], landmarks[i][1]) for i in LANDMARK_IDX],
        dtype=np.float64
    )
    focal_length  = w
    camera_matrix = np.array([
        [focal_length, 0, w / 2],
        [0, focal_length, h / 2],
        [0, 0, 1]
    ], dtype=np.float64)

    success, rotation_vec, _ = cv2.solvePnP(
        MODEL_POINTS, image_points, camera_matrix, np.zeros((4, 1))
    )
    if not success:
        return 0, 0, 0

    rot_mat, _ = cv2.Rodrigues(rotation_vec)
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rot_mat)
    return round(angles[1], 2), round(angles[0], 2), round(angles[2], 2)


def analyze_frame(b64_frame):
    result = {
        "face_count": 0, "face_present": False, "multiple_faces": False,
        "looking_away": False, "yaw": 0, "pitch": 0, "roll": 0, "flags": []
    }

    try:
        frame = decode_frame(b64_frame)
        if frame is None:
            result["flags"].append("FRAME_DECODE_ERROR")
            return result

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)

        faces = _cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=8,       # strict — reduces false positives
            minSize=(80, 80),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        face_count = len(faces) if len(faces) > 0 else 0
        result["face_count"]   = face_count
        result["face_present"] = face_count > 0

        if face_count == 0:
            result["flags"].append("NO_FACE")
            _face_count_buffer.clear()
            return result

        # ── Multiple face check: only flag if 3 consecutive frames show 2+ ────
        _face_count_buffer.append(face_count)
        if (len(_face_count_buffer) == 3 and
                all(c > 1 for c in _face_count_buffer)):
            result["multiple_faces"] = True
            result["flags"].append("MULTIPLE_FACES")

        # ── Head pose from landmarks on largest face ───────────────────────────
        x, y, w, h  = max(faces, key=lambda f: f[2] * f[3])
        faces_rect   = np.array([[x, y, w, h]])   # shape (1,4) required by LBF

        ok, landmarks_list = _get_facemark().fit(gray, faces_rect)
        if ok and len(landmarks_list) > 0:
            lm = landmarks_list[0][0]   # shape (68, 2)
            yaw, pitch, roll = get_head_pose(lm, frame.shape)
            result["yaw"], result["pitch"], result["roll"] = yaw, pitch, roll

            if abs(yaw) > HEAD_POSE_YAW_THRESH or abs(pitch) > HEAD_POSE_PITCH_THRESH:
                result["looking_away"] = True
                result["flags"].append("LOOKING_AWAY")

    except Exception as e:
        import traceback; traceback.print_exc()
        result["flags"].append(f"ANALYSIS_ERROR: {str(e)}")

    return result
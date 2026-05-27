import os

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH   = os.path.join(BASE_DIR, "database", "proctor.db")
REPORTS_DIR     = os.path.join(BASE_DIR, "reports")
LOGS_DIR        = os.path.join(BASE_DIR, "logs")

# ─── Flask ────────────────────────────────────────────────────────────────────
# Reads from environment variable on Render, falls back to dev default locally
SECRET_KEY      = os.environ.get("SECRET_KEY", "proctor_secret_dev_only")
SESSION_TYPE    = "filesystem"

# ─── Cheating Score Weights ───────────────────────────────────────────────────
SCORE_LOOKING_AWAY      = 10
SCORE_TAB_SWITCH        = 20
SCORE_NO_FACE           = 25
SCORE_MOBILE_DETECTED   = 50
SCORE_MULTIPLE_FACES    = 70

# ─── Thresholds ───────────────────────────────────────────────────────────────
NO_FACE_TIMEOUT_SEC     = 5
HEAD_POSE_YAW_THRESH    = 30
HEAD_POSE_PITCH_THRESH  = 20
AUDIO_THRESHOLD         = 500

# ─── Exam ─────────────────────────────────────────────────────────────────────
EXAM_DURATION_SECONDS   = 600
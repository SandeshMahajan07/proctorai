"""
Exam routes:
  GET  /exam           — serve exam page
  POST /api/submit     — submit exam answers
  POST /api/log        — log a violation from frontend
  POST /api/analyze    — analyze webcam frame (face + objects)
  GET  /result/<id>    — show result page
"""

import json
import os
from flask import (Blueprint, render_template, request, session,
                   redirect, url_for, jsonify, flash)
from database.db import (create_exam_session, end_exam_session,
                          log_violation, get_session, get_violations,
                          get_answers, save_answer)
from ai_modules.face_detector  import analyze_frame
from ai_modules.object_detector import detect_objects
from ai_modules.audio_monitor   import analyze_audio_level
from config import (SCORE_LOOKING_AWAY, SCORE_TAB_SWITCH, SCORE_NO_FACE,
                    SCORE_MOBILE_DETECTED, SCORE_MULTIPLE_FACES, EXAM_DURATION_SECONDS)

exam_bp = Blueprint("exam", __name__)

# ── Load questions once ────────────────────────────────────────────────────────
QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "questions.json")
with open(QUESTIONS_PATH) as f:
    QUESTIONS = json.load(f)

# ─── Score map for violation types ────────────────────────────────────────────
VIOLATION_SCORES = {
    "TAB_SWITCH":       SCORE_TAB_SWITCH,
    "WINDOW_BLUR":      SCORE_TAB_SWITCH,
    "NO_FACE":          SCORE_NO_FACE,
    "MULTIPLE_FACES":   SCORE_MULTIPLE_FACES,
    "LOOKING_AWAY":     SCORE_LOOKING_AWAY,
    "MOBILE_DETECTED":  SCORE_MOBILE_DETECTED,
    "AUDIO_DETECTED":   10,
}

def login_required(f):
    """Simple decorator to enforce login."""
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper

# ─────────────────────────────────────────────────────────────────────────────
#  PAGES
# ─────────────────────────────────────────────────────────────────────────────

@exam_bp.route("/exam")
@login_required
def exam_page():
    """Render the exam interface. Creates a new exam session."""
    # Create a new exam session for this student
    session_id = create_exam_session(session["user_id"])
    session["exam_session_id"] = session_id
    return render_template(
        "exam.html",
        questions=QUESTIONS,
        duration=EXAM_DURATION_SECONDS,
        session_id=session_id,
        username=session["username"]
    )

@exam_bp.route("/result/<int:session_id>")
@login_required
def result_page(session_id):
    """Show post-exam result + violations report."""
    exam_sess  = get_session(session_id)
    violations = get_violations(session_id)
    answers    = get_answers(session_id)

    if not exam_sess:
        flash("Session not found.", "error")
        return redirect(url_for("exam.exam_page"))

    # Build violation summary
    violation_summary = {}
    for v in violations:
        vtype = v["violation_type"]
        violation_summary[vtype] = violation_summary.get(vtype, 0) + 1

    # Cheating risk level
    score = exam_sess["cheating_score"]
    if score == 0:
        risk = ("LOW", "green")
    elif score < 100:
        risk = ("MEDIUM", "orange")
    elif score < 200:
        risk = ("HIGH", "red")
    else:
        risk = ("VERY HIGH", "darkred")

    return render_template(
        "result.html",
        exam_sess=exam_sess,
        violations=violations,
        violation_summary=violation_summary,
        answers=answers,
        questions=QUESTIONS,
        risk=risk,
        total_questions=len(QUESTIONS)
    )

# ─────────────────────────────────────────────────────────────────────────────
#  APIs
# ─────────────────────────────────────────────────────────────────────────────

@exam_bp.route("/api/submit", methods=["POST"])
@login_required
def submit_exam():
    """
    Submit exam answers.
    Body: { session_id, answers: [{question_id, answer}, ...] }
    """
    data       = request.get_json()
    session_id = data.get("session_id") or session.get("exam_session_id")
    answers    = data.get("answers", [])

    correct = 0
    q_map   = {q["id"]: q["answer"] for q in QUESTIONS}

    for ans in answers:
        qid        = ans["question_id"]
        user_ans   = ans["answer"]
        is_correct = (user_ans == q_map.get(qid))
        if is_correct:
            correct += 1
        save_answer(session_id, qid, user_ans, is_correct)

    end_exam_session(session_id, correct)

    return jsonify({
        "success":    True,
        "score":      correct,
        "total":      len(QUESTIONS),
        "redirect":   url_for("exam.result_page", session_id=session_id)
    })

@exam_bp.route("/api/log", methods=["POST"])
@login_required
def log_event():
    """
    Log a frontend-detected violation.
    Body: { session_id, violation_type, description }
    """
    data           = request.get_json()
    session_id     = data.get("session_id") or session.get("exam_session_id")
    violation_type = data.get("violation_type", "UNKNOWN")
    description    = data.get("description", "")

    points = VIOLATION_SCORES.get(violation_type, 5)
    log_violation(session_id, violation_type, description, points)

    return jsonify({"success": True, "points_added": points})

@exam_bp.route("/api/analyze", methods=["POST"])
@login_required
def analyze_webcam():
    """
    Analyze a webcam frame for face + object violations.
    Body: { session_id, frame: "<base64 image>", run_yolo: bool }
    """
    data       = request.get_json()
    session_id = data.get("session_id") or session.get("exam_session_id")
    b64_frame  = data.get("frame", "")
    run_yolo   = data.get("run_yolo", False)  # YOLO runs less frequently (every 5s)

    all_flags  = []

    # ── Face analysis ──────────────────────────────────────────────────────────
    face_result = analyze_frame(b64_frame)
    all_flags  += face_result.get("flags", [])

    # ── Object detection (optional, throttled) ─────────────────────────────────
    obj_result  = {"phone_detected": False, "flags": []}
    if run_yolo:
        obj_result  = detect_objects(b64_frame)
        all_flags  += obj_result.get("flags", [])

    # ── Log each unique flag as a violation ────────────────────────────────────
    logged = []
    for flag in set(all_flags):  # deduplicate flags in same frame
        if flag in VIOLATION_SCORES:
            points = VIOLATION_SCORES[flag]
            log_violation(session_id, flag, f"Auto-detected: {flag}", points)
            logged.append({"flag": flag, "points": points})

    return jsonify({
        "success":     True,
        "face":        face_result,
        "objects":     obj_result,
        "flags":       all_flags,
        "logged":      logged
    })

@exam_bp.route("/api/audio", methods=["POST"])
@login_required
def analyze_audio():
    """
    Receive audio RMS level from frontend.
    Body: { session_id, rms: float }
    """
    data       = request.get_json()
    session_id = data.get("session_id") or session.get("exam_session_id")
    rms        = float(data.get("rms", 0))

    audio_result = analyze_audio_level(rms)

    if audio_result["is_loud"]:
        log_violation(session_id, "AUDIO_DETECTED",
                      f"Audio RMS={rms:.0f} exceeded threshold", 10)

    return jsonify({"success": True, "audio": audio_result})
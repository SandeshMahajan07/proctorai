"""Admin dashboard routes."""

from flask import Blueprint, render_template, session, redirect, url_for, flash
from database.db import get_all_sessions_with_users, get_session, get_violations, get_answers
from ai_modules.face_detector import analyze_frame  # unused here but imported for structure

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper

@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    all_sessions = get_all_sessions_with_users()

    # Compute statistics
    total_exams     = len(all_sessions)
    avg_cheat_score = (
        sum(s["cheating_score"] for s in all_sessions) / total_exams
        if total_exams else 0
    )
    high_risk = sum(1 for s in all_sessions if s["cheating_score"] >= 100)

    return render_template(
        "admin/dashboard.html",
        sessions=all_sessions,
        total_exams=total_exams,
        avg_cheat_score=round(avg_cheat_score, 1),
        high_risk=high_risk
    )

@admin_bp.route("/report/<int:session_id>")
@admin_required
def student_report(session_id):
    from database.db import get_answers
    import json, os
    questions_path = os.path.join(os.path.dirname(__file__), "..", "static", "questions.json")
    with open(questions_path) as f:
        questions = json.load(f)

    exam_sess  = get_session(session_id)
    violations = get_violations(session_id)
    answers    = get_answers(session_id)

    if not exam_sess:
        flash("Session not found.", "error")
        return redirect(url_for("admin.dashboard"))

    # Violation type counts
    v_counts = {}
    for v in violations:
        t = v["violation_type"]
        v_counts[t] = v_counts.get(t, 0) + 1

    score = exam_sess["cheating_score"]
    if   score == 0:       risk = ("CLEAN",     "#22c55e")
    elif score < 100:      risk = ("MEDIUM",    "#f59e0b")
    elif score < 200:      risk = ("HIGH",      "#ef4444")
    else:                  risk = ("VERY HIGH", "#7f1d1d")

    return render_template(
        "admin/student_report.html",
        exam_sess=exam_sess,
        violations=violations,
        v_counts=v_counts,
        answers=answers,
        questions=questions,
        risk=risk
    )
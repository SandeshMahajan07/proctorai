"""Authentication routes — login, logout."""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from database.db import verify_user

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/", methods=["GET"])
def index():
    """Redirect root to login or exam based on session."""
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("exam.exam_page"))
    return redirect(url_for("auth.login"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = verify_user(username, password)
        if user:
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            session["role"]     = user["role"]
            flash("Login successful!", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("exam.exam_page"))
        else:
            flash("Invalid credentials. Try again.", "error")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))
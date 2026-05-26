"""
ProctorAI — AI-Based Online Exam Cheating Detection System
Entry point. Initializes Flask app, registers blueprints, sets up DB.
"""

import os
from flask import Flask
from flask_session import Session
from config import SECRET_KEY, SESSION_TYPE
from database.db import init_db
from routes.auth  import auth_bp
from routes.exam  import exam_bp
from routes.admin import admin_bp

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Config ──────────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"]    = SECRET_KEY
    app.config["SESSION_TYPE"]  = SESSION_TYPE
    app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "flask_sessions")
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

    Session(app)  # Initialize server-side sessions

    # ── Initialize database ─────────────────────────────────────────────────────
    init_db()

    # ── Register blueprints ─────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(admin_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    print("=" * 60)
    print("  ProctorAI — Exam Proctoring System")
    print("  Running at: http://127.0.0.1:5000")
    print("  Admin:   username=admin    password=admin123")
    print("  Student: username=student1 password=student123")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
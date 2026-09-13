from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ..extensions import db
from ..models import User, utcnow

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.is_active and user.check_password(request.form.get("password", "")):
            login_user(user, remember=bool(request.form.get("remember")))
            user.last_login_at = utcnow(); db.session.commit()
            return redirect(url_for("main.dashboard"))
        flash("Email atau kata sandi tidak valid.", "error")
    return render_template("auth/login.html")


@bp.post("/logout")
def logout():
    logout_user()
    flash("Anda telah keluar.", "success")
    return redirect(url_for("auth.login"))

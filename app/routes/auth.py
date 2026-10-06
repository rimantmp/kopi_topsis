from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ..extensions import db
from ..models import Role, User, utcnow

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


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not name or not email:
            flash("Nama dan email wajib diisi.", "error")
        elif len(password) < 8:
            flash("Kata sandi minimal 8 karakter.", "error")
        elif password != confirm_password:
            flash("Konfirmasi kata sandi tidak sesuai.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Email sudah terdaftar. Silakan masuk.", "error")
        else:
            role = Role.query.filter_by(name="petani").first()
            if not role:
                role = Role(name="petani", description="Petani kopi")
                db.session.add(role); db.session.flush()
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user); db.session.commit()
            login_user(user)
            flash("Akun petani berhasil dibuat. Selamat datang!", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html")


@bp.post("/logout")
def logout():
    logout_user()
    flash("Anda telah keluar.", "success")
    return redirect(url_for("auth.login"))

from datetime import datetime, timezone
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import AuditLog, Criterion, RecommendationResult, RecommendationSession, Role, Subcriterion, User, Variety
from ..utils import roles_required

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    from flask import redirect, url_for
    return redirect(url_for("main.dashboard"))


@bp.get("/dashboard")
@login_required
def dashboard():
    now = datetime.now(timezone.utc)
    month_query = RecommendationSession.query.filter(
        func.extract("year", RecommendationSession.created_at) == now.year,
        func.extract("month", RecommendationSession.created_at) == now.month,
    )
    if current_user.is_farmer:
        month_query = month_query.filter_by(user_id=current_user.id)
    month_count = month_query.count()
    recent_query = RecommendationSession.query
    if not (current_user.is_admin or current_user.is_department_head):
        recent_query = recent_query.filter_by(user_id=current_user.id)
    recent = recent_query.order_by(RecommendationSession.created_at.desc()).limit(8).all()
    return render_template(
        "dashboard.html",
        variety_count=Variety.query.filter_by(is_active=True).count(),
        criterion_count=Criterion.query.filter_by(is_active=True).count(),
        recommendation_count=(RecommendationSession.query.filter_by(status="completed", user_id=current_user.id).count() if current_user.is_farmer else RecommendationSession.query.filter_by(status="completed").count()),
        month_count=month_count,
        recent=recent,
        farmer_count=User.query.join(Role).filter(Role.name.in_(["petani", "user"]), User.is_active_flag.is_(True)).count(),
        top_varieties=db.session.query(Variety.name, func.count(RecommendationResult.id).label("total")).join(RecommendationResult).filter(RecommendationResult.rank_no == 1).group_by(Variety.id, Variety.name).order_by(func.count(RecommendationResult.id).desc()).limit(5).all(),
    )


@bp.get("/reports")
@login_required
@roles_required("admin", "kepala_dinas")
def reports():
    sessions = RecommendationSession.query.filter_by(status="completed").order_by(RecommendationSession.created_at.desc()).all()
    return render_template("reports.html", sessions=sessions)


@bp.get("/farmers")
@login_required
@roles_required("admin", "kepala_dinas")
def farmers():
    items = User.query.join(Role).filter(Role.name.in_(["petani", "user"])).order_by(User.name).all()
    return render_template("farmers.html", items=items)


@bp.get("/references")
@login_required
@roles_required("petani", "user", "kepala_dinas")
def references():
    return render_template(
        "references.html",
        varieties=Variety.query.filter_by(is_active=True).order_by(Variety.code).all(),
        criteria=Criterion.query.filter_by(is_active=True).order_by(Criterion.display_order).all(),
        subcriteria=Subcriterion.query.filter_by(is_active=True).order_by(Subcriterion.criterion_id, Subcriterion.display_order).all(),
    )


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not name or not email:
            flash("Nama dan email wajib diisi.", "error")
        elif User.query.filter(User.email == email, User.id != current_user.id).first():
            flash("Email sudah digunakan oleh akun lain.", "error")
        elif new_password and len(new_password) < 8:
            flash("Kata sandi baru minimal 8 karakter.", "error")
        elif new_password and not current_user.check_password(current_password):
            flash("Kata sandi saat ini tidak sesuai.", "error")
        elif new_password != confirm_password:
            flash("Konfirmasi kata sandi baru tidak sesuai.", "error")
        else:
            before = {"name": current_user.name, "email": current_user.email}
            current_user.name = name; current_user.email = email
            if new_password: current_user.set_password(new_password)
            db.session.add(AuditLog(user_id=current_user.id, action="update_profile", entity_type="user", entity_id=str(current_user.id), before_data=before, after_data={"name": name, "email": email, "password_changed": bool(new_password)}))
            db.session.commit(); flash("Profil berhasil diperbarui.", "success")
            return redirect(url_for("main.profile"))
    return render_template("profile.html")

from datetime import datetime, timezone
from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from ..models import Criterion, RecommendationSession, Variety
from ..utils import admin_required

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    from flask import redirect, url_for
    return redirect(url_for("main.dashboard"))


@bp.get("/dashboard")
@login_required
def dashboard():
    now = datetime.now(timezone.utc)
    month_count = RecommendationSession.query.filter(
        func.extract("year", RecommendationSession.created_at) == now.year,
        func.extract("month", RecommendationSession.created_at) == now.month,
    ).count()
    recent_query = RecommendationSession.query
    if not current_user.is_admin:
        recent_query = recent_query.filter_by(user_id=current_user.id)
    recent = recent_query.order_by(RecommendationSession.created_at.desc()).limit(8).all()
    return render_template(
        "dashboard.html",
        variety_count=Variety.query.filter_by(is_active=True).count(),
        criterion_count=Criterion.query.filter_by(is_active=True).count(),
        recommendation_count=RecommendationSession.query.filter_by(status="completed").count(),
        month_count=month_count,
        recent=recent,
    )


@bp.get("/reports")
@login_required
@admin_required
def reports():
    sessions = RecommendationSession.query.filter_by(status="completed").order_by(RecommendationSession.created_at.desc()).all()
    return render_template("reports.html", sessions=sessions)

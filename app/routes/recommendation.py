from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (Criterion, Location, RecommendationInput, RecommendationResult,
                      RecommendationSession, TopsisCalculation, Variety,
                      VarietyScore, utcnow)
from ..services.topsis_service import TopsisValidationError, calculate_topsis

bp = Blueprint("recommendation", __name__)


def calculation_data():
    criteria = Criterion.query.filter_by(is_active=True).order_by(Criterion.display_order, Criterion.code).all()
    varieties = Variety.query.filter_by(is_active=True).order_by(Variety.code).all()
    if not criteria:
        raise TopsisValidationError("Belum ada kriteria aktif.")
    matrix = []
    for variety in varieties:
        by_criterion = {row.criterion_id: row for row in variety.scores}
        if any(criterion.id not in by_criterion for criterion in criteria):
            raise TopsisValidationError(f"Nilai varietas {variety.name} belum lengkap.")
        matrix.append([float(by_criterion[c.id].score) for c in criteria])
    output = calculate_topsis(matrix, [float(c.weight) for c in criteria], [c.attribute_type for c in criteria])
    return criteria, varieties, output


@bp.route("/recommendation", methods=["GET", "POST"])
@login_required
def create():
    criteria = Criterion.query.filter_by(is_active=True).order_by(Criterion.display_order).all()
    locations = Location.query.filter_by(is_active=True).order_by(Location.name).all()
    if request.method == "POST":
        try:
            location_id = request.form.get("location_id", type=int)
            location = db.session.get(Location, location_id) if location_id else None
            if not location:
                raise TopsisValidationError("Lokasi wajib dipilih.")
            location_name = location.name
            calc_criteria, varieties, output = calculation_data()
            snapshot = [{"id": c.id, "code": c.code, "name": c.name, "weight": float(c.weight), "attribute": c.attribute_type} for c in calc_criteria]
            session = RecommendationSession(user_id=current_user.id, location_id=location.id, location_name=location_name, status="processing", criteria_snapshot=snapshot)
            db.session.add(session); db.session.flush()
            for criterion in calc_criteria:
                sub_id = request.form.get(f"input_{criterion.id}", type=int)
                sub = next((s for s in criterion.subcriteria if s.id == sub_id and s.is_active), None)
                if not sub:
                    raise TopsisValidationError(f"Input {criterion.code} wajib dipilih.")
                db.session.add(RecommendationInput(session_id=session.id, criterion_id=criterion.id, raw_value=sub.technical_range, mapped_score=sub.score, mapping_snapshot={"name": sub.name, "range": sub.technical_range, "score": float(sub.score)}))
            db.session.add(TopsisCalculation(session_id=session.id, decision_matrix=output["decision_matrix"], normalization_matrix=output["normalization_matrix"], weighted_matrix=output["weighted_matrix"], positive_ideal=output["positive_ideal"], negative_ideal=output["negative_ideal"]))
            for rank, index in enumerate(output["ranking"], 1):
                db.session.add(RecommendationResult(session_id=session.id, variety_id=varieties[index].id, rank_no=rank, distance_positive=output["distance_positive"][index], distance_negative=output["distance_negative"][index], preference_score=output["preferences"][index]))
            session.status = "completed"; session.completed_at = utcnow(); db.session.commit()
            return redirect(url_for("recommendation.result", session_id=session.id))
        except TopsisValidationError as exc:
            db.session.rollback(); flash(str(exc), "error")
        except Exception:
            db.session.rollback(); raise
    return render_template("recommendation/form.html", criteria=criteria, locations=locations)


@bp.get("/topsis")
@login_required
def topsis():
    return redirect(url_for("recommendation.create"))


@bp.post("/topsis/calculate")
@login_required
def topsis_calculate():
    return create()


def authorized_session(session_id):
    session = db.get_or_404(RecommendationSession, session_id)
    if not (current_user.is_admin or current_user.is_department_head) and session.user_id != current_user.id:
        abort(403)
    return session


@bp.get("/recommendation/result/<session_id>")
@login_required
def result(session_id):
    session = authorized_session(session_id)
    results = sorted(session.results, key=lambda row: row.rank_no)
    return render_template("recommendation/result.html", session=session, results=results, print_mode=False)


@bp.get("/topsis/result/<session_id>")
@login_required
def topsis_result(session_id):
    return result(session_id)


@bp.get("/history")
@login_required
def history():
    query = RecommendationSession.query
    if not (current_user.is_admin or current_user.is_department_head):
        query = query.filter_by(user_id=current_user.id)
    return render_template("recommendation/history.html", sessions=query.order_by(RecommendationSession.created_at.desc()).all())


@bp.get("/reports/<session_id>/print")
@login_required
def print_result(session_id):
    session = authorized_session(session_id)
    return render_template("recommendation/result.html", session=session, results=sorted(session.results, key=lambda row: row.rank_no), print_mode=True)

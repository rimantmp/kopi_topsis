from decimal import Decimal, InvalidOperation
import re
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import AuditLog, Criterion, Location, Subcriterion, User, Variety, VarietyScore
from ..utils import admin_required

bp = Blueprint("master", __name__)


def next_code(model, prefix, padding=0):
    """Buat kode numerik berikutnya tanpa mengasumsikan data selalu berurutan."""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
    numbers = []
    for (code,) in db.session.query(model.code).all():
        match = pattern.match(code or "")
        if match:
            numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    return f"{prefix}{number:0{padding}d}" if padding else f"{prefix}{number}"


def audit(action, entity, entity_id, after=None):
    db.session.add(AuditLog(user_id=current_user.id, action=action, entity_type=entity, entity_id=str(entity_id), after_data=after))


def commit_or_flash(message="Data berhasil disimpan."):
    try:
        db.session.commit(); flash(message, "success"); return True
    except IntegrityError:
        db.session.rollback(); flash("Kode atau nama sudah digunakan.", "error"); return False


@bp.route("/criteria", methods=["GET", "POST"])
@login_required
@admin_required
def criteria():
    edit_id = request.args.get("edit", type=int)
    edited = db.session.get(Criterion, edit_id) if edit_id else None
    suggested_code = next_code(Criterion, "C")
    if request.method == "POST":
        item = db.session.get(Criterion, request.form.get("id", type=int)) if request.form.get("id") else Criterion()
        try:
            item.code = (request.form.get("code") or suggested_code).strip().upper()
            item.name = request.form["name"].strip()
            item.weight = Decimal(request.form["weight"]) / Decimal(100)
            item.attribute_type = request.form["attribute_type"]
            item.unit = request.form.get("unit", "").strip() or None
            item.display_order = request.form.get("display_order", type=int) or 0
            item.is_active = bool(request.form.get("is_active"))
            if not item.code or not item.name or item.attribute_type not in {"benefit", "cost"} or item.weight < 0:
                raise ValueError
            db.session.add(item); db.session.flush(); audit("save", "criterion", item.id, {"code": item.code, "name": item.name})
            if commit_or_flash(): return redirect(url_for("master.criteria"))
        except (InvalidOperation, ValueError, KeyError):
            db.session.rollback(); flash("Periksa kembali data kriteria.", "error")
    items = Criterion.query.order_by(Criterion.display_order, Criterion.code).all()
    return render_template("master/criteria.html", items=items, edited=edited, suggested_code=suggested_code)


@bp.post("/criteria/<int:item_id>/toggle")
@login_required
@admin_required
def criterion_toggle(item_id):
    item = db.get_or_404(Criterion, item_id); item.is_active = not item.is_active
    audit("toggle", "criterion", item.id, {"is_active": item.is_active}); commit_or_flash("Status kriteria diperbarui.")
    return redirect(url_for("master.criteria"))


@bp.route("/subcriteria", methods=["GET", "POST"])
@login_required
@admin_required
def subcriteria():
    edit_id = request.args.get("edit", type=int)
    edited = db.session.get(Subcriterion, edit_id) if edit_id else None
    if request.method == "POST":
        item = db.session.get(Subcriterion, request.form.get("id", type=int)) if request.form.get("id") else Subcriterion()
        try:
            item.criterion_id = int(request.form["criterion_id"])
            item.name = request.form["name"].strip(); item.technical_range = request.form["technical_range"].strip()
            item.score = Decimal(request.form["score"]); item.display_order = request.form.get("display_order", type=int) or 0
            item.is_active = bool(request.form.get("is_active"))
            if not item.name or not item.technical_range or item.score < 0: raise ValueError
            db.session.add(item); db.session.flush(); audit("save", "subcriterion", item.id)
            if commit_or_flash(): return redirect(url_for("master.subcriteria"))
        except (ValueError, InvalidOperation, KeyError):
            db.session.rollback(); flash("Periksa kembali data subkriteria.", "error")
    return render_template("master/subcriteria.html", items=Subcriterion.query.order_by(Subcriterion.criterion_id, Subcriterion.display_order).all(), criteria=Criterion.query.order_by(Criterion.display_order).all(), edited=edited)


@bp.route("/weights", methods=["GET", "POST"])
@login_required
@admin_required
def weights():
    items = Criterion.query.filter_by(is_active=True).order_by(Criterion.display_order).all()
    if request.method == "POST":
        try:
            values = [Decimal(request.form[f"weight_{item.id}"]) for item in items]
            if any(v < 0 for v in values) or abs(sum(values) - Decimal("100")) > Decimal("0.000001"):
                raise ValueError
            for item, value in zip(items, values): item.weight = value / Decimal(100)
            audit("update", "weights", "active", {item.code: str(item.weight) for item in items})
            db.session.commit(); flash("Bobot 100% berhasil disimpan.", "success")
            return redirect(url_for("master.weights"))
        except (ValueError, InvalidOperation, KeyError):
            db.session.rollback(); flash("Total bobot harus tepat 100% dan tidak negatif.", "error")
    return render_template("master/weights.html", items=items)


@bp.route("/varieties", methods=["GET", "POST"])
@login_required
@admin_required
def varieties():
    edit_id = request.args.get("edit", type=int); edited = db.session.get(Variety, edit_id) if edit_id else None
    suggested_code = next_code(Variety, "V", padding=3)
    if request.method == "POST":
        item = db.session.get(Variety, request.form.get("id", type=int)) if request.form.get("id") else Variety()
        item.code = (request.form.get("code") or suggested_code).strip().upper(); item.name = request.form.get("name", "").strip()
        item.description = request.form.get("description", "").strip() or None; item.is_active = bool(request.form.get("is_active"))
        if not item.code or not item.name: flash("Kode dan nama wajib diisi.", "error")
        else:
            db.session.add(item); db.session.flush(); audit("save", "variety", item.id, {"code": item.code, "name": item.name})
            if commit_or_flash(): return redirect(url_for("master.varieties"))
    query = request.args.get("q", "").strip()
    items_query = Variety.query
    if query: items_query = items_query.filter(Variety.name.contains(query) | Variety.code.contains(query))
    return render_template("master/varieties.html", items=items_query.order_by(Variety.code).all(), edited=edited, query=query, suggested_code=suggested_code)


@bp.post("/varieties/<int:item_id>/toggle")
@login_required
@admin_required
def variety_toggle(item_id):
    item = db.get_or_404(Variety, item_id); item.is_active = not item.is_active
    audit("toggle", "variety", item.id, {"is_active": item.is_active}); commit_or_flash("Status varietas diperbarui.")
    return redirect(url_for("master.varieties"))


@bp.route("/locations", methods=["GET", "POST"])
@login_required
@admin_required
def locations():
    edit_id = request.args.get("edit", type=int); edited = db.session.get(Location, edit_id) if edit_id else None
    if request.method == "POST":
        item = db.session.get(Location, request.form.get("id", type=int)) if request.form.get("id") else Location()
        item.name = request.form.get("name", "").strip()
        item.description = request.form.get("description", "").strip() or None
        item.is_active = bool(request.form.get("is_active"))
        if not item.name: flash("Nama lokasi wajib diisi.", "error")
        else:
            db.session.add(item); db.session.flush(); audit("save", "location", item.id, {"name": item.name})
            if commit_or_flash(): return redirect(url_for("master.locations"))
    query = request.args.get("q", "").strip()
    items_query = Location.query
    if query: items_query = items_query.filter(Location.name.contains(query) | Location.description.contains(query))
    return render_template("master/locations.html", items=items_query.order_by(Location.name).all(), edited=edited, query=query)


@bp.post("/locations/<int:item_id>/toggle")
@login_required
@admin_required
def location_toggle(item_id):
    item = db.get_or_404(Location, item_id); item.is_active = not item.is_active
    audit("toggle", "location", item.id, {"is_active": item.is_active}); commit_or_flash("Status lokasi diperbarui.")
    return redirect(url_for("master.locations"))


@bp.route("/alternative-scores", methods=["GET", "POST"])
@login_required
@admin_required
def scores():
    criteria_items = Criterion.query.filter_by(is_active=True).order_by(Criterion.display_order).all()
    varieties_items = Variety.query.filter_by(is_active=True).order_by(Variety.code).all()
    if request.method == "POST":
        try:
            for variety in varieties_items:
                for criterion in criteria_items:
                    value = Decimal(request.form[f"score_{variety.id}_{criterion.id}"])
                    allowed_scores = {Decimal(str(sub.score)) for sub in criterion.subcriteria if sub.is_active}
                    if value < 0 or value not in allowed_scores:
                        raise ValueError
                    row = VarietyScore.query.filter_by(variety_id=variety.id, criterion_id=criterion.id).first()
                    if not row: row = VarietyScore(variety_id=variety.id, criterion_id=criterion.id)
                    row.score = value; db.session.add(row)
            audit("update", "variety_scores", "matrix"); db.session.commit(); flash("Matriks nilai berhasil disimpan.", "success")
            return redirect(url_for("master.scores"))
        except (KeyError, InvalidOperation, ValueError):
            db.session.rollback(); flash("Semua nilai wajib dipilih dari subkriteria yang aktif.", "error")
    score_map = {(s.variety_id, s.criterion_id): s.score for s in VarietyScore.query.all()}
    return render_template("master/scores.html", criteria=criteria_items, varieties=varieties_items, score_map=score_map)


@bp.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():
    from ..models import Role
    roles = Role.query.order_by(Role.name).all()
    edit_id = request.args.get("edit", type=int)
    edited = db.session.get(User, edit_id) if edit_id else None
    if request.method == "POST":
        user_id = request.form.get("id", type=int)
        user = db.session.get(User, user_id) if user_id else User()
        if user is None:
            flash("Pengguna tidak ditemukan.", "error")
            return redirect(url_for("master.users"))
        name = request.form.get("name", "").strip(); email = request.form.get("email", "").strip().lower(); password = request.form.get("password", "")
        role = db.session.get(Role, request.form.get("role_id", type=int))
        is_active = bool(request.form.get("is_active"))
        if not name or not email or (password and len(password) < 8) or (not user_id and len(password) < 8) or not role:
            flash("Data tidak valid; kata sandi pengguna baru minimal 8 karakter.", "error")
        elif user.id == current_user.id and (not is_active or role.name != "admin"):
            flash("Akun admin yang sedang digunakan tidak dapat dinonaktifkan atau diubah rolenya.", "error")
        else:
            user.name = name; user.email = email; user.role = role; user.is_active_flag = is_active
            if password: user.set_password(password)
            db.session.add(user); db.session.flush()
            audit("save", "user", user.id, {"name": user.name, "email": user.email, "role": role.name, "is_active": is_active})
            message = "Pengguna berhasil diperbarui." if user_id else "Pengguna berhasil dibuat."
            if commit_or_flash(message): return redirect(url_for("master.users"))
    return render_template("master/users.html", items=User.query.order_by(User.name).all(), roles=roles, edited=edited)


@bp.post("/users/<int:item_id>/toggle")
@login_required
@admin_required
def user_toggle(item_id):
    item = db.get_or_404(User, item_id)
    if item.id == current_user.id:
        flash("Akun yang sedang digunakan tidak dapat dinonaktifkan.", "error")
    else:
        item.is_active_flag = not item.is_active_flag
        audit("toggle", "user", item.id, {"is_active": item.is_active_flag})
        commit_or_flash("Status pengguna diperbarui.")
    return redirect(url_for("master.users"))

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Criterion, Role, Subcriterion, User


CRITERIA = [
    ("C1", "Kesesuaian ketinggian tempat", 0.20, "mdpl"),
    ("C2", "Kesesuaian suhu lingkungan", 0.07, "°C"),
    ("C3", "Kesesuaian curah hujan", 0.05, "mm/tahun"),
    ("C4", "Produktivitas", 0.30, "kg/ha/tahun"),
    ("C5", "Ketahanan terhadap hama dan penyakit", 0.08, None),
    ("C6", "Cita rasa kopi", 0.30, "skor"),
]

SUBCRITERIA = {
    "C1": [("Sangat tidak sesuai", 1, "0–500 mdpl"), ("Tidak sesuai", 2, "300–500 mdpl"), ("Cukup sesuai", 3, "700 mdpl"), ("Sesuai", 4, "1000–1200 mdpl"), ("Sangat sesuai", 5, "1200–3000 mdpl")],
    "C2": [("Sangat tidak sesuai", 1, "30–36 °C"), ("Tidak sesuai", 2, "23–30 °C"), ("Cukup sesuai", 3, "21–23 °C"), ("Sesuai", 4, "19–21 °C"), ("Sangat sesuai", 5, "16–19 °C")],
    "C3": [("Sangat tidak sesuai", 1, "300–500 mm/tahun"), ("Tidak sesuai", 2, "500–700 mm/tahun"), ("Cukup sesuai", 3, "700–900 mm/tahun"), ("Sesuai", 4, "1200–1400 mm/tahun"), ("Sangat sesuai", 5, ">1500 mm/tahun")],
    "C4": [("Sangat rendah", 1, "100–300 kg/ha/tahun"), ("Rendah", 2, "300–500 kg/ha/tahun"), ("Sedang", 3, "600–800 kg/ha/tahun"), ("Tinggi", 4, "800–1000 kg/ha/tahun"), ("Sangat tinggi", 5, "1000–1200 kg/ha/tahun")],
    "C5": [("Sangat rentan", 1, "Jamur akar"), ("Rentan", 2, "Malayensis"), ("Cukup tahan", 3, "Jamur upas"), ("Tahan", 4, "PBKO"), ("Sangat tahan", 5, "KBK")],
    "C6": [("Sangat rendah", 1, "Skor 50–60"), ("Rendah", 2, "Skor 60–70"), ("Sedang", 3, "Skor 70–75"), ("Baik", 4, "Skor 75–80"), ("Sangat baik", 5, "Skor 80–90")],
}


@click.command("init-db")
@click.option("--admin-email", default="admin@kopi.local", show_default=True)
@click.option("--admin-password", default="Admin123!", show_default=True)
@click.option("--refresh-seed/--no-refresh-seed", default=True, show_default=True)
@with_appcontext
def init_db(admin_email, admin_password, refresh_seed):
    db.create_all()
    admin_role = Role.query.filter_by(name="admin").first() or Role(name="admin", description="Administrator")
    user_role = Role.query.filter_by(name="user").first() or Role(name="user", description="Pengguna")
    db.session.add_all([admin_role, user_role]); db.session.flush()
    admin = User.query.filter_by(email=admin_email.lower()).first()
    if not admin:
        admin = User(name="Administrator", email=admin_email.lower(), role=admin_role)
        admin.set_password(admin_password); db.session.add(admin)
    elif refresh_seed:
        admin.role = admin_role
        admin.is_active_flag = True
        admin.set_password(admin_password)
    for order, (code, name, weight, unit) in enumerate(CRITERIA, 1):
        criterion = Criterion.query.filter_by(code=code).first()
        if not criterion:
            criterion = Criterion(code=code, name=name, weight=weight, unit=unit, attribute_type="benefit", display_order=order)
            db.session.add(criterion); db.session.flush()
        elif refresh_seed:
            criterion.name = name
            criterion.weight = weight
            criterion.unit = unit
            criterion.attribute_type = "benefit"
            criterion.display_order = order
            criterion.is_active = True
        for sub_order, (sub_name, score, technical_range) in enumerate(SUBCRITERIA[code], 1):
            sub = Subcriterion.query.filter_by(criterion_id=criterion.id, name=sub_name).first()
            if not sub:
                db.session.add(Subcriterion(criterion=criterion, name=sub_name, score=score, technical_range=technical_range, display_order=sub_order))
            elif refresh_seed:
                sub.score = score
                sub.technical_range = technical_range
                sub.display_order = sub_order
                sub.is_active = True
    db.session.commit()
    click.echo(f"Database dan seed siap. Admin: {admin_email}")


def register_commands(app):
    app.cli.add_command(init_db)

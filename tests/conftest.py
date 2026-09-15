import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Criterion, Role, Subcriterion, User, Variety, VarietyScore


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        admin_role = Role(name="admin")
        user_role = Role(name="user")
        farmer_role = Role(name="petani")
        head_role = Role(name="kepala_dinas")
        db.session.add_all([admin_role, user_role, farmer_role, head_role]); db.session.flush()
        admin = User(name="Admin", email="admin@test.local", role=admin_role); admin.set_password("Admin123!")
        user = User(name="User", email="user@test.local", role=user_role); user.set_password("User123!")
        farmer = User(name="Petani", email="petani@test.local", role=farmer_role); farmer.set_password("Petani123!")
        head = User(name="Kepala Dinas", email="kadis@test.local", role=head_role); head.set_password("Kadis123!")
        criteria = [Criterion(code=f"C{i+1}", name=f"Kriteria {i+1}", weight=w, attribute_type="benefit", display_order=i+1) for i, w in enumerate([.2,.07,.05,.3,.08,.3])]
        db.session.add_all([admin, user, farmer, head, *criteria]); db.session.flush()
        for c in criteria:
            db.session.add(Subcriterion(criterion=c, name="Sesuai", technical_range="Simulasi", score=4, display_order=1))
        varieties = [Variety(code=f"A{i+1}", name=f"Alternatif {i+1}") for i in range(4)]
        db.session.add_all(varieties); db.session.flush()
        matrix = [[5,4,4,3,4,5],[4,5,3,4,3,4],[3,3,5,5,5,3],[4,4,4,4,4,4]]
        for variety, row in zip(varieties, matrix):
            for criterion, score in zip(criteria, row):
                db.session.add(VarietyScore(variety_id=variety.id, criterion_id=criterion.id, score=score))
        db.session.commit()
        yield app
        db.session.remove(); db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email="admin@test.local", password="Admin123!"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)

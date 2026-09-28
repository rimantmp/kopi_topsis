from tests.conftest import login


def test_login_and_dashboard(client):
    response = login(client)
    assert response.status_code == 200
    assert b"Ringkasan sistem" in response.data
    assert b"Kopi Terbaik, Keputusan Tepat" in response.data
    assert b'class="active" href="/dashboard"' in response.data
    assert b'id="logoutDialog"' in response.data
    assert b'id="confirmLogout"' in response.data


def test_login_page_uses_toraja_split_layout(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"auth-visual" in response.data
    assert b"login-toraja.png" not in response.data  # image is loaded by project CSS
    assert b"togglePassword" in response.data
    assert b"Dari Tana Toraja" in response.data


def test_recommendation_full_flow(client, app):
    from app.models import Criterion, Location
    from app.extensions import db
    login(client)
    with app.app_context():
        criteria = Criterion.query.order_by(Criterion.display_order).all()
        payload = {f"input_{c.id}": str(c.subcriteria[0].id) for c in criteria}
        loc = Location(name="Lokasi Uji"); db.session.add(loc); db.session.commit()
        payload["location_id"] = str(loc.id)
    response = client.post("/recommendation", data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Hasil Rekomendasi" in response.data
    assert b"Alternatif 1" in response.data
    assert b"0.5444" in response.data

    from app.models import RecommendationSession
    with app.app_context():
        session_id = RecommendationSession.query.one().id
    printed = client.get(f"/reports/{session_id}/print")
    assert printed.status_code == 200
    assert b"LAPORAN HASIL REKOMENDASI" in printed.data
    assert b"Input Kondisi" in printed.data
    assert b"Ranking Hasil TOPSIS" in printed.data
    assert b"Solusi Ideal" in printed.data


def test_recommendation_requires_location(client, app):
    from app.models import Criterion, RecommendationSession
    login(client)
    page = client.get("/recommendation")
    assert b'name="location_id" required' in page.data
    assert b'name="location_name"' not in page.data
    with app.app_context():
        criteria = Criterion.query.order_by(Criterion.display_order).all()
        payload = {f"input_{c.id}": str(c.subcriteria[0].id) for c in criteria}
    response = client.post("/recommendation", data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Lokasi wajib dipilih" in response.data
    with app.app_context():
        assert RecommendationSession.query.count() == 0


def test_user_cannot_access_admin_master(client):
    login(client, "user@test.local", "User123!")
    response = client.get("/criteria")
    assert response.status_code == 403


def test_users_page_uses_table_search_and_modal(client):
    from .conftest import login
    login(client)
    response = client.get("/users")
    assert response.status_code == 200
    assert b'id="userSearch"' in response.data
    assert b'id="userModal"' in response.data
    assert b'id="userTable"' in response.data


def test_admin_can_edit_and_toggle_user(client, app):
    from .conftest import login
    from app.extensions import db
    from app.models import User
    login(client)
    with app.app_context():
        user = User.query.filter_by(email="user@test.local").one()
        user_id = user.id
        role_id = user.role_id
    response = client.post("/users", data={"id": user_id, "name": "Pengguna Baru", "email": "baru@test.local", "password": "", "role_id": role_id, "is_active": "on"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Pengguna Baru" in response.data
    client.post(f"/users/{user_id}/toggle", follow_redirects=True)
    with app.app_context():
        assert db.session.get(User, user_id).is_active is False


def test_farmer_pages_and_access_boundaries(client):
    from .conftest import login
    login(client, "petani@test.local", "Petani123!")
    assert b"Dashboard Petani" in client.get("/dashboard").data
    assert client.get("/references").status_code == 200
    assert client.get("/profile").status_code == 200
    assert client.get("/farmers").status_code == 403
    assert client.get("/reports").status_code == 403
    assert client.get("/criteria").status_code == 403


def test_department_head_pages_and_read_only_access(client):
    from .conftest import login
    login(client, "kadis@test.local", "Kadis123!")
    assert b"Dashboard Eksekutif" in client.get("/dashboard").data
    assert client.get("/farmers").status_code == 200
    assert client.get("/reports").status_code == 200
    assert client.get("/references").status_code == 200
    assert client.get("/criteria").status_code == 403


def test_profile_page_and_secure_password_change(client, app):
    from .conftest import login
    from app.models import User
    login(client)
    page = client.get("/profile")
    assert page.status_code == 200
    assert b"Informasi Pribadi" in page.data
    assert b"Keamanan Akun" in page.data
    response = client.post("/profile", data={"name": "Admin", "email": "admin@test.local", "current_password": "salah", "new_password": "PasswordBaru123!", "confirm_password": "PasswordBaru123!"}, follow_redirects=True)
    assert b"Kata sandi saat ini tidak sesuai" in response.data
    with app.app_context():
        assert not User.query.filter_by(email="admin@test.local").one().check_password("PasswordBaru123!")
    response = client.post("/profile", data={"name": "Admin Baru", "email": "admin@test.local", "current_password": "Admin123!", "new_password": "PasswordBaru123!", "confirm_password": "PasswordBaru123!"}, follow_redirects=True)
    assert b"Profil berhasil diperbarui" in response.data
    with app.app_context():
        user = User.query.filter_by(email="admin@test.local").one()
        assert user.name == "Admin Baru"
        assert user.check_password("PasswordBaru123!")


def test_bad_login_is_rejected(client):
    response = client.post("/login", data={"email": "admin@test.local", "password": "wrong"}, follow_redirects=True)
    assert b"tidak valid" in response.data


def test_subcriteria_page_is_grouped_and_searchable(client):
    login(client)
    response = client.get("/subcriteria")
    assert response.status_code == 200
    assert b"subcriteriaSearch" in response.data
    assert b"subcriterionModal" in response.data
    assert b"criterion-accordion" in response.data
    assert b"Kriteria 1" in response.data


def test_criteria_page_uses_table_and_modal(client):
    login(client)
    response = client.get("/criteria")
    assert response.status_code == 200
    assert b"criteriaTable" in response.data
    assert b"criteriaSearch" in response.data
    assert b"criterionModal" in response.data
    assert b'value="C7"' in response.data
    assert b"Dibuat otomatis oleh sistem" in response.data


def test_varieties_page_uses_table_and_modal(client):
    login(client)
    response = client.get("/varieties")
    assert response.status_code == 200
    assert b"varietyTable" in response.data
    assert b"varietySearch" in response.data
    assert b"varietyModal" in response.data
    assert b'value="V001"' in response.data
    assert b"Dibuat otomatis oleh sistem" in response.data


def test_locations_page_uses_table_and_modal(client):
    login(client)
    response = client.get("/locations")
    assert response.status_code == 200
    assert b"locationTable" in response.data
    assert b"locationSearch" in response.data
    assert b"locationModal" in response.data


def test_location_dropdown_flows_into_recommendation(client, app):
    from app.extensions import db
    from app.models import Criterion, Location, RecommendationSession
    login(client)
    with app.app_context():
        loc = Location(name="Lembang Rantepao", description="Kecamatan Rantepao")
        db.session.add(loc); db.session.commit()
        criteria = Criterion.query.order_by(Criterion.display_order).all()
        payload = {f"input_{c.id}": str(c.subcriteria[0].id) for c in criteria}
        loc_id = loc.id
    payload["location_id"] = str(loc_id)
    payload["location_name"] = ""
    response = client.post("/recommendation", data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Hasil Rekomendasi" in response.data
    with app.app_context():
        sess = RecommendationSession.query.one()
        assert sess.location_id == loc_id
        assert sess.location_name == "Lembang Rantepao"


def test_recommendation_page_uses_simple_table_form(client):
    login(client)
    response = client.get("/recommendation")
    assert response.status_code == 200
    assert b"recommendation-table" in response.data
    assert b"completionText" in response.data
    assert b"processingOverlay" in response.data


def test_weights_page_shows_table_and_live_total(client):
    login(client)
    response = client.get("/weights")
    assert response.status_code == 200
    assert b"weight-table" in response.data
    assert b"weightProgress" in response.data
    assert b"weightStatus" in response.data


def test_alternative_scores_show_subcriterion_descriptions(client):
    login(client)
    response = client.get("/alternative-scores")
    assert response.status_code == 200
    assert b"score-subcriterion" in response.data
    assert b"Sesuai" in response.data
    assert b"Simulasi" in response.data
    assert b"matrixCompletion" in response.data

from tests.conftest import login


def test_login_and_dashboard(client):
    response = login(client)
    assert response.status_code == 200
    assert b"Ringkasan sistem" in response.data
    assert b"Kopi Terbaik, Keputusan Tepat" in response.data
    assert b'class="active" href="/dashboard"' in response.data


def test_login_page_uses_toraja_split_layout(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"auth-visual" in response.data
    assert b"login-toraja.png" not in response.data  # image is loaded by project CSS
    assert b"togglePassword" in response.data
    assert b"Dari Tana Toraja" in response.data


def test_recommendation_full_flow(client, app):
    from app.models import Criterion
    login(client)
    with app.app_context():
        criteria = Criterion.query.order_by(Criterion.display_order).all()
        payload = {f"input_{c.id}": str(c.subcriteria[0].id) for c in criteria}
    payload["location_name"] = "Lokasi Uji"
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


def test_user_cannot_access_admin_master(client):
    login(client, "user@test.local", "User123!")
    response = client.get("/criteria")
    assert response.status_code == 403


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

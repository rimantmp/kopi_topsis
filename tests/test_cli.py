def test_init_db_refreshes_seed_without_deleting_operational_data(app):
    from app.extensions import db
    from app.models import Criterion, Variety

    with app.app_context():
        criterion = Criterion.query.filter_by(code="C1").first()
        criterion.weight = 0.99
        existing_count = Variety.query.count()
        db.session.commit()

    runner = app.test_cli_runner()
    result = runner.invoke(args=["init-db", "--admin-email", "admin@test.local", "--admin-password", "NewPassword123!"])
    assert result.exit_code == 0

    with app.app_context():
        assert float(Criterion.query.filter_by(code="C1").first().weight) == 0.20
        assert Variety.query.count() == existing_count

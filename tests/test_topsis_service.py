import pytest

from app.services.topsis_service import TopsisValidationError, calculate_topsis, validate_weights


MATRIX = [[5,4,4,3,4,5],[4,5,3,4,3,4],[3,3,5,5,5,3],[4,4,4,4,4,4]]
WEIGHTS = [.2,.07,.05,.3,.08,.3]


def test_golden_topsis_result():
    result = calculate_topsis(MATRIX, WEIGHTS, ["benefit"] * 6)
    assert result["ranking"] == [0, 3, 1, 2]
    assert result["preferences"] == pytest.approx([.5444, .4919, .4613, .5], abs=5e-5)


def test_cost_criterion_reverses_ideal():
    result = calculate_topsis([[1], [2]], [1], ["cost"])
    assert result["positive_ideal"][0] < result["negative_ideal"][0]
    assert result["ranking"] == [0, 1]


def test_invalid_weight_total_is_rejected():
    with pytest.raises(TopsisValidationError, match="Total bobot"):
        validate_weights([.2, .2])


def test_zero_column_is_rejected():
    with pytest.raises(TopsisValidationError, match="nol"):
        calculate_topsis([[0], [0]], [1], ["benefit"])

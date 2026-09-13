import math


class TopsisValidationError(ValueError):
    pass


def validate_weights(weights, tolerance=1e-9):
    if not weights or any(not math.isfinite(float(w)) or float(w) < 0 for w in weights):
        raise TopsisValidationError("Bobot harus berupa angka nonnegatif.")
    if not math.isclose(sum(map(float, weights)), 1.0, abs_tol=tolerance):
        raise TopsisValidationError(f"Total bobot harus 1 (saat ini {sum(map(float, weights)):.6f}).")


def validate_matrix(matrix):
    if len(matrix) < 2:
        raise TopsisValidationError("Minimal dua varietas aktif diperlukan.")
    width = len(matrix[0]) if matrix else 0
    if not width or any(len(row) != width for row in matrix):
        raise TopsisValidationError("Matriks keputusan tidak valid.")
    if any(not math.isfinite(float(value)) for row in matrix for value in row):
        raise TopsisValidationError("Matriks hanya boleh berisi angka finite.")
    if any(math.isclose(sum(float(row[j]) ** 2 for row in matrix), 0.0) for j in range(width)):
        raise TopsisValidationError("Kolom matriks bernilai nol dan tidak dapat dinormalisasi.")


def normalize_matrix(matrix):
    validate_matrix(matrix)
    denominators = [math.sqrt(sum(float(row[j]) ** 2 for row in matrix)) for j in range(len(matrix[0]))]
    return [[float(value) / denominators[j] for j, value in enumerate(row)] for row in matrix]


def calculate_weighted_matrix(normalized, weights):
    validate_weights(weights)
    if normalized and len(normalized[0]) != len(weights):
        raise TopsisValidationError("Jumlah bobot tidak sama dengan jumlah kriteria.")
    return [[value * float(weights[j]) for j, value in enumerate(row)] for row in normalized]


def calculate_ideal_solutions(weighted, attribute_types):
    if not weighted or len(weighted[0]) != len(attribute_types):
        raise TopsisValidationError("Atribut kriteria tidak lengkap.")
    positive, negative = [], []
    for j, kind in enumerate(attribute_types):
        values = [row[j] for row in weighted]
        if kind == "benefit":
            positive.append(max(values)); negative.append(min(values))
        elif kind == "cost":
            positive.append(min(values)); negative.append(max(values))
        else:
            raise TopsisValidationError("Atribut harus benefit atau cost.")
    return positive, negative


def calculate_distances(weighted, positive, negative):
    distance_positive = [math.sqrt(sum((value - positive[j]) ** 2 for j, value in enumerate(row))) for row in weighted]
    distance_negative = [math.sqrt(sum((value - negative[j]) ** 2 for j, value in enumerate(row))) for row in weighted]
    return distance_positive, distance_negative


def calculate_preferences(distance_positive, distance_negative):
    preferences = []
    for d_pos, d_neg in zip(distance_positive, distance_negative):
        denominator = d_pos + d_neg
        if math.isclose(denominator, 0.0, abs_tol=1e-15):
            raise TopsisValidationError("Alternatif identik; nilai preferensi tidak dapat dibedakan.")
        preferences.append(d_neg / denominator)
    return preferences


def calculate_topsis(matrix, weights, attribute_types):
    validate_weights(weights)
    normalized = normalize_matrix(matrix)
    weighted = calculate_weighted_matrix(normalized, weights)
    positive, negative = calculate_ideal_solutions(weighted, attribute_types)
    distance_positive, distance_negative = calculate_distances(weighted, positive, negative)
    preferences = calculate_preferences(distance_positive, distance_negative)
    ranking = sorted(range(len(matrix)), key=lambda i: (-preferences[i], i))
    return {
        "decision_matrix": [[float(v) for v in row] for row in matrix],
        "normalization_matrix": normalized,
        "weighted_matrix": weighted,
        "positive_ideal": positive,
        "negative_ideal": negative,
        "distance_positive": distance_positive,
        "distance_negative": distance_negative,
        "preferences": preferences,
        "ranking": ranking,
    }

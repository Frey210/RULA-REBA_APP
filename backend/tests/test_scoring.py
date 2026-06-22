from app.services.scoring import calculate_reba_score, calculate_rula_score

NEUTRAL_ANGLES = {
    "neck": 5,
    "trunk": 3,
    "ua_l": 10,
    "ua_r": 12,
    "la_l": 85,
    "la_r": 90,
    "wrist_l": 4,
    "wrist_r": 5,
    "leg_l": 10,
    "leg_r": 12,
    "wrist_twist": 1,
}

HIGH_RISK_ANGLES = {
    "neck": 35,
    "trunk": 70,
    "trunk_twist_bend": 1,
    "neck_twist_bend": 1,
    "ua_l": 110,
    "ua_r": 95,
    "ua_l_mod": 1,
    "ua_r_mod": 1,
    "la_l": 30,
    "la_r": 145,
    "wrist_l": 35,
    "wrist_r": 40,
    "leg_l": 75,
    "leg_r": 10,
    "wrist_twist": 2,
}


def test_reba_neutral_score_is_low() -> None:
    result = calculate_reba_score(NEUTRAL_ANGLES, {"load_score": 0, "coupling_score": 0, "activity_score": 0})
    assert result["assessment_type"] == "reba"
    assert result["score"] <= 3
    assert result["risk_level"] in {"Negligible", "Low"}


def test_reba_high_risk_score_increases_with_manual_factors() -> None:
    result = calculate_reba_score(HIGH_RISK_ANGLES, {"load_score": 2, "coupling_score": 2, "activity_score": 2})
    assert result["score"] >= 10
    assert result["risk_level"] in {"High", "Very High"}
    assert result["breakdown"]["load_score"] == 2


def test_rula_neutral_score_is_acceptable_or_investigate() -> None:
    result = calculate_rula_score(NEUTRAL_ANGLES, {"load_score": 0, "activity_score": 0, "wrist_twist_score": 1})
    assert result["assessment_type"] == "rula"
    assert result["score"] <= 4
    assert result["risk_level"] in {"Acceptable", "Further Investigate"}


def test_rula_high_risk_score_increases_with_manual_factors() -> None:
    result = calculate_rula_score(HIGH_RISK_ANGLES, {"load_score": 2, "activity_score": 1, "wrist_twist_score": 2})
    assert result["score"] >= 6
    assert result["risk_level"] in {"Investigate Soon", "Investigate Immediately"}
    assert result["breakdown"]["twist_score"] == 2


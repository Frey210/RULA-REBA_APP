from typing import Literal

AssessmentType = Literal["rula", "reba"]

TABLE_A_REBA = [
    [[1, 2, 3, 4], [1, 2, 3, 4], [3, 3, 5, 6]],
    [[2, 3, 4, 5], [3, 4, 5, 6], [4, 5, 6, 7]],
    [[2, 4, 5, 6], [4, 5, 6, 7], [5, 6, 7, 8]],
    [[3, 5, 6, 7], [5, 6, 7, 8], [6, 7, 8, 9]],
    [[4, 6, 7, 8], [6, 7, 8, 9], [7, 8, 9, 9]],
]

TABLE_B_REBA = [
    [[1, 2, 2], [1, 2, 3]],
    [[1, 2, 3], [2, 3, 4]],
    [[3, 4, 5], [4, 5, 5]],
    [[4, 5, 5], [5, 6, 7]],
    [[6, 7, 8], [7, 8, 8]],
    [[7, 8, 8], [8, 9, 9]],
]

TABLE_C_REBA = [
    [1, 1, 1, 2, 3, 3, 4, 5, 6, 7, 7, 7],
    [1, 2, 2, 3, 4, 4, 5, 6, 6, 7, 7, 8],
    [2, 3, 3, 3, 4, 5, 6, 7, 7, 8, 8, 8],
    [3, 4, 4, 4, 5, 6, 7, 8, 8, 9, 9, 9],
    [4, 4, 4, 5, 6, 7, 8, 8, 9, 9, 9, 9],
    [6, 6, 6, 7, 8, 8, 9, 9, 10, 10, 10, 10],
    [7, 7, 7, 8, 9, 9, 9, 10, 10, 11, 11, 11],
    [8, 8, 8, 9, 10, 10, 10, 10, 10, 11, 11, 11],
    [9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12],
    [10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 12],
    [11, 11, 11, 11, 12, 12, 12, 12, 12, 12, 12, 12],
    [12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12],
]

TABLE_A_RULA = [
    [
        [[1, 2], [2, 2], [2, 3], [3, 3]],
        [[2, 2], [2, 2], [3, 3], [3, 3]],
        [[2, 3], [3, 3], [3, 3], [4, 4]],
    ],
    [
        [[2, 3], [3, 3], [3, 4], [4, 4]],
        [[3, 3], [3, 3], [3, 4], [4, 4]],
        [[3, 4], [4, 4], [4, 4], [5, 5]],
    ],
    [
        [[3, 3], [4, 4], [4, 4], [5, 5]],
        [[3, 4], [4, 4], [4, 4], [5, 5]],
        [[4, 4], [4, 4], [4, 5], [5, 5]],
    ],
    [
        [[4, 4], [4, 4], [4, 5], [5, 5]],
        [[4, 4], [4, 4], [4, 5], [5, 5]],
        [[4, 4], [4, 5], [5, 5], [6, 6]],
    ],
    [
        [[5, 5], [5, 5], [5, 6], [6, 7]],
        [[5, 6], [6, 6], [6, 7], [7, 7]],
        [[6, 6], [6, 7], [7, 7], [7, 8]],
    ],
    [
        [[7, 7], [7, 7], [7, 8], [8, 9]],
        [[8, 8], [8, 8], [8, 9], [9, 9]],
        [[9, 9], [9, 9], [9, 9], [9, 9]],
    ],
]

TABLE_B_RULA = [
    [[1, 3], [2, 3], [3, 4], [5, 5], [6, 6], [7, 7]],
    [[2, 3], [2, 3], [4, 5], [5, 5], [6, 7], [7, 7]],
    [[3, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 7]],
    [[5, 5], [5, 6], [6, 7], [7, 7], [7, 7], [8, 8]],
    [[7, 7], [7, 7], [7, 8], [8, 8], [8, 8], [8, 8]],
    [[8, 8], [8, 8], [8, 8], [8, 9], [9, 9], [9, 9]],
]

TABLE_C_RULA = [
    [1, 2, 3, 3, 4, 5, 5],
    [2, 2, 3, 4, 4, 5, 5],
    [3, 3, 3, 4, 4, 5, 6],
    [3, 3, 3, 4, 5, 6, 6],
    [4, 4, 4, 5, 6, 7, 7],
    [4, 4, 5, 6, 6, 7, 7],
    [5, 5, 6, 6, 7, 7, 7],
    [5, 5, 6, 7, 7, 7, 7],
]


def clamp(value: int | float, minimum: int, maximum: int) -> int:
    return max(minimum, min(int(value), maximum))


def lookup_reba_a(trunk: int, neck: int, leg: int) -> int:
    return TABLE_A_REBA[clamp(trunk, 1, 5) - 1][clamp(neck, 1, 3) - 1][clamp(leg, 1, 4) - 1]


def lookup_reba_b(upper_arm: int, lower_arm: int, wrist: int) -> int:
    return TABLE_B_REBA[clamp(upper_arm, 1, 6) - 1][clamp(lower_arm, 1, 2) - 1][
        clamp(wrist, 1, 3) - 1
    ]


def lookup_reba_c(score_a: int, score_b: int) -> int:
    return TABLE_C_REBA[clamp(score_a, 1, 12) - 1][clamp(score_b, 1, 12) - 1]


def lookup_rula_a(upper_arm: int, lower_arm: int, wrist: int, twist: int) -> int:
    return TABLE_A_RULA[clamp(upper_arm, 1, 6) - 1][clamp(lower_arm, 1, 3) - 1][
        clamp(wrist, 1, 4) - 1
    ][clamp(twist, 1, 2) - 1]


def lookup_rula_b(neck: int, trunk: int, legs: int) -> int:
    return TABLE_B_RULA[clamp(neck, 1, 6) - 1][clamp(trunk, 1, 6) - 1][
        clamp(legs, 1, 2) - 1
    ]


def lookup_rula_c(score_a: int, score_b: int) -> int:
    return TABLE_C_RULA[clamp(score_a, 1, 8) - 1][clamp(score_b, 1, 7) - 1]


def calculate_reba_score(angles: dict, manual: dict | None = None) -> dict:
    manual = manual or {}

    neck_angle = float(angles.get("neck", 0))
    neck_score = 2 if neck_angle < 0 or neck_angle > 20 else 1
    neck_score = clamp(neck_score + int(angles.get("neck_twist_bend", 0)), 1, 3)

    trunk_angle = float(angles.get("trunk", 0))
    if -5 <= trunk_angle <= 5:
        trunk_score = 1
    elif trunk_angle < -5:
        trunk_score = 2 if trunk_angle >= -20 else 3
    elif trunk_angle <= 20:
        trunk_score = 2
    elif trunk_angle <= 60:
        trunk_score = 3
    else:
        trunk_score = 4
    trunk_score = clamp(trunk_score + int(angles.get("trunk_twist_bend", 0)), 1, 5)

    leg_l = float(angles.get("leg_l", 0))
    leg_r = float(angles.get("leg_r", 0))
    leg_score = 2 if abs(leg_l - leg_r) > 40 else 1
    max_knee_flex = max(leg_l, leg_r)
    if max_knee_flex > 60:
        leg_score += 2
    elif max_knee_flex >= 30:
        leg_score += 1
    leg_score = clamp(leg_score, 1, 4)

    score_a = lookup_reba_a(trunk_score, neck_score, leg_score)
    load_score = clamp(manual.get("load_score", 0), 0, 3)
    score_a += load_score

    def upper_arm_score(value: float) -> int:
        if -20 <= value <= 20:
            return 1
        if value < -20 or value <= 45:
            return 2
        if value <= 90:
            return 3
        return 4

    ua_score = max(
        upper_arm_score(float(angles.get("ua_l", 0))) + int(angles.get("ua_l_mod", 0)),
        upper_arm_score(float(angles.get("ua_r", 0))) + int(angles.get("ua_r_mod", 0)),
    )
    ua_score = clamp(ua_score, 1, 6)

    def lower_arm_score(value: float) -> int:
        return 1 if 60 <= value <= 100 else 2

    la_score = max(
        lower_arm_score(float(angles.get("la_l", 0))),
        lower_arm_score(float(angles.get("la_r", 0))),
    )
    la_score = clamp(la_score, 1, 2)

    def wrist_score_for(value: float) -> int:
        return 1 if value <= 15 else 2

    wrist_score = max(
        wrist_score_for(float(angles.get("wrist_l", 0))),
        wrist_score_for(float(angles.get("wrist_r", 0))),
    )
    wrist_score = clamp(wrist_score, 1, 3)

    score_b = lookup_reba_b(ua_score, la_score, wrist_score)
    coupling_score = clamp(manual.get("coupling_score", 0), 0, 3)
    score_b += coupling_score

    final_score = lookup_reba_c(score_a, score_b)
    activity_score = clamp(manual.get("activity_score", 0), 0, 2)
    final_score += activity_score

    return {
        "assessment_type": "reba",
        "score": final_score,
        "risk_level": get_reba_risk_level(final_score),
        "breakdown": {
            "score_a": score_a,
            "score_b": score_b,
            "trunk_score": trunk_score,
            "neck_score": neck_score,
            "leg_score": leg_score,
            "ua_score": ua_score,
            "la_score": la_score,
            "wrist_score": wrist_score,
            "load_score": load_score,
            "coupling_score": coupling_score,
            "activity_score": activity_score,
        },
    }


def calculate_rula_score(angles: dict, manual: dict | None = None) -> dict:
    manual = manual or {}

    def upper_arm_score(value: float) -> int:
        if -20 <= value <= 20:
            return 1
        if value < -20 or value <= 45:
            return 2
        if value <= 90:
            return 3
        return 4

    ua_score = max(
        upper_arm_score(float(angles.get("ua_l", 0))) + int(angles.get("ua_l_mod", 0)),
        upper_arm_score(float(angles.get("ua_r", 0))) + int(angles.get("ua_r_mod", 0)),
    )
    ua_score = clamp(ua_score, 1, 6)

    def lower_arm_score(value: float) -> int:
        return 1 if 60 <= value <= 100 else 2

    la_score = max(
        lower_arm_score(float(angles.get("la_l", 0))),
        lower_arm_score(float(angles.get("la_r", 0))),
    )
    la_score = clamp(la_score, 1, 3)

    def wrist_score_for(value: float) -> int:
        if value <= 5:
            return 1
        if value <= 15:
            return 2
        return 3

    wrist_score = max(
        wrist_score_for(float(angles.get("wrist_l", 0))),
        wrist_score_for(float(angles.get("wrist_r", 0))),
    )
    wrist_score = clamp(wrist_score, 1, 4)

    twist_score = clamp(manual.get("wrist_twist_score", angles.get("wrist_twist", 1)), 1, 2)
    score_a = lookup_rula_a(ua_score, la_score, wrist_score, twist_score)

    muscle_a = clamp(manual.get("activity_score", 0), 0, 1)
    force_a = clamp(manual.get("load_score", 0), 0, 3)
    score_a += muscle_a + force_a

    neck_angle = float(angles.get("neck", 0))
    if neck_angle < 0:
        neck_score = 4
    elif neck_angle <= 10:
        neck_score = 1
    elif neck_angle <= 20:
        neck_score = 2
    else:
        neck_score = 3
    neck_score = clamp(neck_score + int(angles.get("neck_twist_bend", 0)), 1, 6)

    trunk_angle = float(angles.get("trunk", 0))
    if -5 <= trunk_angle <= 5:
        trunk_score = 1
    elif trunk_angle < -5:
        trunk_score = 2
    elif trunk_angle <= 20:
        trunk_score = 2
    elif trunk_angle <= 60:
        trunk_score = 3
    else:
        trunk_score = 4
    trunk_score = clamp(trunk_score + int(angles.get("trunk_twist_bend", 0)), 1, 6)

    leg_score = 2 if abs(float(angles.get("leg_l", 0)) - float(angles.get("leg_r", 0))) > 40 else 1
    leg_score = clamp(leg_score, 1, 2)

    score_b = lookup_rula_b(neck_score, trunk_score, leg_score)
    muscle_b = muscle_a
    force_b = force_a
    score_b += muscle_b + force_b

    final_score = lookup_rula_c(score_a, score_b)

    return {
        "assessment_type": "rula",
        "score": final_score,
        "risk_level": get_rula_risk_level(final_score),
        "breakdown": {
            "score_a": score_a,
            "score_b": score_b,
            "ua_score": ua_score,
            "la_score": la_score,
            "wrist_score": wrist_score,
            "twist_score": twist_score,
            "neck_score": neck_score,
            "trunk_score": trunk_score,
            "leg_score": leg_score,
            "muscle_a": muscle_a,
            "force_a": force_a,
            "muscle_b": muscle_b,
            "force_b": force_b,
        },
    }


def calculate_score(assessment_type: AssessmentType, angles: dict, manual: dict | None = None) -> dict:
    if assessment_type == "reba":
        return calculate_reba_score(angles, manual)
    return calculate_rula_score(angles, manual)


def get_reba_risk_level(score: int) -> str:
    if score == 1:
        return "Negligible"
    if 2 <= score <= 3:
        return "Low"
    if 4 <= score <= 7:
        return "Medium"
    if 8 <= score <= 10:
        return "High"
    return "Very High"


def get_rula_risk_level(score: int) -> str:
    if 1 <= score <= 2:
        return "Acceptable"
    if 3 <= score <= 4:
        return "Further Investigate"
    if 5 <= score <= 6:
        return "Investigate Soon"
    return "Investigate Immediately"


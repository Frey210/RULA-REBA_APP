import math

from app.services.scoring import calculate_score

BODY_COMPONENTS = ("neck", "trunk", "ua_l", "ua_r", "la_l", "la_r", "leg_l", "leg_r")
REQUIRED_COMPONENTS = (*BODY_COMPONENTS, "wrist_l", "wrist_r")


def missing_components(angles: dict) -> list[str]:
    return [key for key in REQUIRED_COMPONENTS if not isinstance(angles.get(key), (int, float))
            or isinstance(angles[key], bool) or not math.isfinite(angles[key])]


def normalize_measurements(detection) -> None:
    metadata = dict(detection.metadata)
    angles = dict(metadata.get("angles") or {})
    for key, value in list(angles.items()):
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)):
            raise ValueError(f"Invalid pose measurement: {key}")
    quality = dict(metadata.get("assessment_quality") or {})
    # Legacy payloads used zero for wrists even when the landmark detector failed.
    if quality.get("wrist_components_measured") == 0:
        angles["wrist_l"] = angles["wrist_r"] = None
    missing = missing_components(angles)
    quality["missing_components"] = missing
    quality["status"] = "insufficient" if any(key in missing for key in BODY_COMPONENTS) else "partial" if missing else "good"
    for kind in ("rula", "reba"):
        metadata[kind] = None
        if not any(key in missing for key in BODY_COMPONENTS):
            estimate = {**angles, **{key: 0 for key in missing}}
            metadata[kind] = {**calculate_score(kind, estimate, {}), "provisional": True,
                              "missing_components": missing}
    detection.metadata = {**metadata, "angles": angles, "assessment_quality": quality}

ANGLE_LABELS = {
    "neck": "Neck", "trunk": "Trunk", "ua_l": "Upper arm - left", "ua_r": "Upper arm - right",
    "la_l": "Lower arm - left", "la_r": "Lower arm - right", "leg_l": "Knee - left",
    "leg_r": "Knee - right", "wrist_l": "Wrist - left", "wrist_r": "Wrist - right",
}


def label(value):
    return str(value).replace("_", " ").capitalize()


def references(data):
    result = {}
    for collection, prefix in (("workers", "W"), ("events", "E"), ("assessments", "A"), ("photos", "P")):
        for index, row in enumerate(data[collection], 1):
            result[row["id"]] = f"{prefix}{index:03}"
    result.update({row["id"]: row["cam_id"] for row in data["cameras"]})
    return result


def flatten(values, prefix=""):
    for key, value in values.items():
        name = f"{prefix}{label(key)}"
        if isinstance(value, dict):
            yield from flatten(value, name + " / ")
        elif isinstance(value, list):
            for index, item in enumerate(value, 1):
                if isinstance(item, dict):
                    yield from flatten(item, f"{name} {index} / ")
                else:
                    yield f"{name} {index}", item
        else:
            yield name, value

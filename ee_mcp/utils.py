from json_repair import repair_json  # type: ignore[misc]


def safe_json_loads(json_str: str) -> str:
    """Safe JSON loads.

    Args:
        json_str: JSON string

    Returns:
        JSON string

    Raises:
        ValueError: If the JSON string is invalid
    """
    res = repair_json(json_str)
    if res == "":
        msg = "Invalid JSON string"
        raise ValueError(msg)
    return res

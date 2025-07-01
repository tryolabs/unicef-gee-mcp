import json
from pathlib import Path

import ee


def initialize_ee(path_to_ee_auth: Path) -> None:
    """Initialize Google Earth Engine with service account credentials.

    Args:
        path_to_ee_auth: Path to the JSON file containing service account credentials
    """
    key_file = path_to_ee_auth.read_text()
    key_dict = json.loads(key_file)
    email = key_dict["client_email"]

    auth = ee.ServiceAccountCredentials(email=email, key_data=key_file)  # type: ignore[call-arg]
    ee.Initialize(auth)

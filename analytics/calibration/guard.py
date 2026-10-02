import os
import json
from typing import List

MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/race_manifest.json'))

class HoldoutContaminationError(ValueError):
    pass

def load_manifest() -> List[dict]:
    if not os.path.exists(MANIFEST_PATH):
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")
    with open(MANIFEST_PATH, 'r') as f:
        return json.load(f)

def get_calibration_races() -> List[int]:
    """Returns a list of session_keys that are explicitly marked as CALIBRATION."""
    manifest = load_manifest()
    return [r['session_key'] for r in manifest if r['split'] == 'CALIBRATION']

def get_holdout_races() -> List[int]:
    """Returns a list of session_keys that are explicitly marked as HOLDOUT."""
    manifest = load_manifest()
    return [r['session_key'] for r in manifest if r['split'] == 'HOLDOUT']

def check_calibration_access(session_keys: List[int]) -> None:
    """
    Guards access to data for empirical model calibration.
    Fails loudly if any session_key is marked as HOLDOUT.
    """
    holdout_races = get_holdout_races()
    
    for session_key in session_keys:
        if session_key in holdout_races:
            raise HoldoutContaminationError(f"Holdout race {session_key} cannot be used for calibration.")

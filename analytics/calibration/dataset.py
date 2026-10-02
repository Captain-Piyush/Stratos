import pandas as pd
import logging
import os
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any

from analytics.calibration.guard import check_calibration_access
from analytics.features.builder import build_feature_dataset
from database.connection import db

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/calibration/cache'))
PROGRESS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/calibration/progress.json'))

def _get_cache_path(session_key: int) -> str:
    return os.path.join(CACHE_DIR, f"{session_key}.csv")

def _load_progress() -> Dict[str, Any]:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {}

def _save_progress(progress: Dict[str, Any]):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=4)

def build_calibration_dataset(session_keys: List[int], force: bool = False) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Builds a calibration dataset from the specified session keys using caching.
    """
    check_calibration_access(session_keys)
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    progress = _load_progress()
    all_dfs = []
    
    stats = {
        "races_processed": 0,
        "raw_observations": 0,
        "valid_observations": 0,
        "excluded_observations": 0,
        "exclusion_reasons": {
            "pit_lap": 0,
            "safety_car": 0,
            "vsc": 0,
            "red_flag": 0,
            "invalid_lap_time": 0,
            "missing_features": 0
        }
    }
    
    if not db.client:
        db.connect()
        
    for i, session_key in enumerate(session_keys, 1):
        str_key = str(session_key)
        
        # Check cache
        cache_path = _get_cache_path(session_key)
        df = None
        
        if not force and os.path.exists(cache_path) and progress.get(str_key, {}).get("status") == "COMPLETE":
            logger.info(f"[{i}/{len(session_keys)}] {session_key}       COMPLETE (Cached) — {progress[str_key].get('rows')} rows")
            try:
                df = pd.read_csv(cache_path)
            except Exception as e:
                logger.warning(f"Failed to read cache for {session_key}: {e}. Rebuilding...")
                df = None
                
        if df is None:
            logger.info(f"[{i}/{len(session_keys)}] {session_key}       PROCESSING...")
            start_time = datetime.now()
            progress[str_key] = {"status": "PROCESSING", "timestamp": start_time.isoformat()}
            _save_progress(progress)
            
            try:
                # build_feature_dataset automatically processes ALL drivers for the session
                df = build_feature_dataset(session_key)
                
                if df is not None and not df.empty:
                    df.to_csv(cache_path, index=False)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    progress[str_key] = {
                        "status": "COMPLETE", 
                        "rows": len(df),
                        "timestamp": datetime.now().isoformat(),
                        "elapsed_seconds": elapsed
                    }
                    logger.info(f"[{i}/{len(session_keys)}] {session_key}       COMPLETE — {len(df)} rows in {elapsed:.1f}s")
                else:
                    raise ValueError("Empty feature dataset returned")
                    
            except Exception as e:
                logger.error(f"[{i}/{len(session_keys)}] {session_key}       FAILED — {e}")
                progress[str_key] = {
                    "status": "FAILED",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
                _save_progress(progress)
                continue
                
        _save_progress(progress)
        
        if df is not None and not df.empty:
            stats["races_processed"] += 1
            stats["raw_observations"] += len(df)
            all_dfs.append(df)
            
    if not all_dfs:
        raise ValueError("No valid calibration data was produced. Check progress.json for failures.")
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Filtering Logic
    mask_pit = combined_df['pit_in'] | combined_df['pit_out']
    stats["exclusion_reasons"]["pit_lap"] = int(mask_pit.sum())
    
    # We might not have 'track_status' in the schema, but we have 'safety_car_active', 'virtual_safety_car_active', 'red_flag_context'
    mask_sc = combined_df['safety_car_active'] == True
    stats["exclusion_reasons"]["safety_car"] = int(mask_sc.sum())
    
    mask_vsc = combined_df['virtual_safety_car_active'] == True
    stats["exclusion_reasons"]["vsc"] = int(mask_vsc.sum())
    
    mask_red = combined_df['red_flag_context'] == True
    stats["exclusion_reasons"]["red_flag"] = int(mask_red.sum())
    
    # invalid lap time is handled by lap_time_valid mostly, but let's double check lap_time
    mask_invalid_time = combined_df['lap_time'].isna() | (combined_df['lap_time'] <= 0) | (combined_df['lap_time'] > 150)
    stats["exclusion_reasons"]["invalid_lap_time"] = int(mask_invalid_time.sum())
    
    mask_missing = combined_df['tyre_compound'].isna() | combined_df['tyre_age'].isna() | (combined_df['tyre_compound'] == 'UNKNOWN')
    stats["exclusion_reasons"]["missing_features"] = int(mask_missing.sum())
    
    mask_exclude = mask_pit | mask_sc | mask_vsc | mask_red | mask_invalid_time | mask_missing
    valid_df = combined_df[~mask_exclude].copy()
    
    stats["excluded_observations"] = int(mask_exclude.sum())
    stats["valid_observations"] = int(len(valid_df))
    
    return valid_df, stats

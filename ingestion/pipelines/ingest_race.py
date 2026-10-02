import os
import sys
import argparse
import logging
from pymongo import UpdateOne
from datetime import datetime, timezone

# Add parent directory to path to allow importing from database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ingestion.openf1.client import OpenF1Client
from database.connection import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ENDPOINTS = {
    'sessions': 'sessions',
    'drivers': 'drivers',
    'laps': 'laps',
    'positions': 'position',
    'stints': 'stints',
    'pit_stops': 'pit',
    'intervals': 'intervals',
    'weather': 'weather',
    'race_control': 'race_control'
}

UNIQUE_KEYS = {
    'sessions': ['session_key'],
    'drivers': ['session_key', 'driver_number'],
    'laps': ['session_key', 'driver_number', 'lap_number'],
    'positions': ['session_key', 'driver_number', 'date'],
    'stints': ['session_key', 'driver_number', 'stint_number'],
    'pit_stops': ['session_key', 'driver_number', 'date'],
    'intervals': ['session_key', 'driver_number', 'date'],
    'weather': ['session_key', 'date'],
    'race_control': ['session_key', 'date', 'message']
}

def setup_indexes():
    """Create unique indexes for idempotent ingestion."""
    for coll_name, keys in UNIQUE_KEYS.items():
        collection = db.get_collection(coll_name)
        index_keys = [(k, 1) for k in keys]
        collection.create_index(index_keys, unique=True)
        
        # Also setup raw collections indexes
        raw_collection = db.get_collection(f"raw_{coll_name}")
        raw_collection.create_index(index_keys, unique=True)

def ingest_dataset(client: OpenF1Client, session_key: int, norm_name: str, endpoint: str):
    """Fetch, save raw, and normalize a dataset."""
    logger.info(f"Fetching {endpoint}...")
    if norm_name == 'sessions':
        data = client.get_sessions(session_key=session_key)
    else:
        data = client.get_dataset(endpoint, session_key)
        
    if not data:
        logger.warning(f"No data retrieved for {norm_name}")
        return 0
        
    # Validation check: Filter out empty or missing core keys
    valid_data = []
    unique_keys = UNIQUE_KEYS[norm_name]
    for doc in data:
        if all(doc.get(k) is not None for k in unique_keys):
            valid_data.append(doc)
        else:
            logger.warning(f"Validation Error: Dropping malformed record in {norm_name}: {doc}")
            
    if not valid_data:
        return 0

    # 1. Store Raw Data
    raw_collection = db.get_collection(f"raw_{norm_name}")
    raw_operations = []
    for doc in valid_data:
        filter_query = {k: doc[k] for k in unique_keys}
        raw_operations.append(UpdateOne(filter_query, {"$set": doc}, upsert=True))
        
    if raw_operations:
        raw_collection.bulk_write(raw_operations)

    # 2. Store Normalized Data
    # For Phase 1, normalized is essentially a clean version of raw, 
    # but in its own collection ready for Phase 2 querying.
    norm_collection = db.get_collection(norm_name)
    norm_operations = []
    for doc in valid_data:
        filter_query = {k: doc[k] for k in unique_keys}
        # Add metadata for normalized records
        doc['_updated_at'] = datetime.now(timezone.utc).isoformat()
        norm_operations.append(UpdateOne(filter_query, {"$set": doc}, upsert=True))

    if norm_operations:
        result = norm_collection.bulk_write(norm_operations)
        # return the number of updated/upserted documents
        return result.upserted_count + result.modified_count
    return 0

def ingest_race(session_key: int):
    logger.info(f"Starting historical ingestion for session_key: {session_key}")
    
    if not db.connect():
        logger.error("Failed to connect to database. Aborting ingestion.")
        sys.exit(1)
        
    setup_indexes()
    client = OpenF1Client()
    
    stats = {}
    for norm_name, endpoint in ENDPOINTS.items():
        try:
            count = ingest_dataset(client, session_key, norm_name, endpoint)
            stats[norm_name] = count
        except Exception as e:
            logger.error(f"Error ingesting {norm_name}: {e}")
            stats[norm_name] = "ERROR"
            
    # Print report
    print(f"\n--- Ingestion Report ---")
    print(f"Session: {session_key}")
    for name, count in stats.items():
        print(f"{name.capitalize()}: {count}")
    print(f"Status: SUCCESS\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest historical F1 race data.")
    parser.add_argument("--session-key", type=int, required=True, help="The OpenF1 session_key to ingest")
    args = parser.parse_args()
    
    ingest_race(args.session_key)

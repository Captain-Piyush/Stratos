import os
import sys
import logging

# Add parent directory to path to allow importing from database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ingestion.openf1.client import OpenF1Client
from database.connection import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_ingestion():
    logger.info("Starting OpenF1 ingestion pipeline")
    
    # 1. Connect to Database
    if not db.connect():
        logger.error("Failed to connect to database. Aborting ingestion.")
        return {"status": "error", "message": "Database connection failed"}
        
    # 2. Fetch Data from OpenF1
    client = OpenF1Client()
    try:
        sessions_data = client.get_sessions(year=2023, country_name="Monaco")
        if not sessions_data:
            logger.warning("No data retrieved from OpenF1")
            return {"status": "success", "message": "No data retrieved", "count": 0}
    except Exception as e:
        logger.error(f"Ingestion failed during data fetch: {e}")
        return {"status": "error", "message": f"Fetch failed: {str(e)}"}
        
    # 3. Store in MongoDB
    try:
        collection = db.get_collection("raw_sessions")
        # Ensure we don't duplicate (simple approach for Phase 0: drop and insert)
        # collection.delete_many({"year": 2023, "country_name": "Monaco"})
        
        result = collection.insert_many(sessions_data)
        count = len(result.inserted_ids)
        logger.info(f"Successfully inserted {count} session records into MongoDB")
        return {"status": "success", "message": f"Inserted {count} records", "count": count, "sample": sessions_data[0]}
    except Exception as e:
        logger.error(f"Ingestion failed during database insert: {e}")
        return {"status": "error", "message": f"Database insert failed: {str(e)}"}

if __name__ == "__main__":
    run_ingestion()

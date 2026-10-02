import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Database:
    def __init__(self):
        self.uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/stratos")
        self.db_name = os.getenv("MONGO_DB_NAME", "stratos")
        self.client = None
        self.db = None

    def connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # The ismaster command is cheap and does not require auth.
            self.client.admin.command('ismaster')
            self.db = self.client[self.db_name]
            logger.info("Successfully connected to MongoDB")
            return True
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
            return False

    def get_collection(self, collection_name):
        if self.db is None:
            raise Exception("Database not connected")
        return self.db[collection_name]

db = Database()

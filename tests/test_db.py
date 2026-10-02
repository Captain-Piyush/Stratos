import os
from unittest.mock import patch
from database.connection import Database

def test_config_loading():
    with patch.dict(os.environ, {"MONGO_URI": "mongodb://test:27017/test", "MONGO_DB_NAME": "test_db"}):
        db = Database()
        assert db.uri == "mongodb://test:27017/test"
        assert db.db_name == "test_db"

def test_db_connection_failure():
    with patch("database.connection.MongoClient") as mock_client:
        from pymongo.errors import ConnectionFailure
        mock_client.side_effect = ConnectionFailure("Mocked connection failure")
        db = Database()
        result = db.connect()
        assert result is False
        assert db.client is None
        assert db.db is None

import os

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure


def init_db() -> tuple[Database, Collection]:
    mongo_uri = os.getenv("MONGO_DB_URI")

    try:
        client: MongoClient = MongoClient(
            mongo_uri,
            maxPoolSize=50,
            connectTimeoutMS=30000,
            serverSelectionTimeoutMS=5000,
        )

        client.admin.command("ping")
        print("✅ Successfully connected to MongoDB Atlas")

    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise SystemExit(1)

    db = client["write2meDB"]
    users_collection: Collection = db["users"]

    try:
        # Create standard indexes
        users_collection.create_index("google_id", unique=True)
        users_collection.create_index("email", unique=True)
        users_collection.create_index([("last_login", -1)])
        print("✅ Database indexes created")

    except Exception as e:
        print(f"❌ Index creation failed: {e}")

    return db, users_collection

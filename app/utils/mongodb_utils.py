from dotenv import load_dotenv
import os
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, HTTPException, Query

load_dotenv()

# MONGODB_URI = os.getenv("MONGODB_URI")
# TAX_MONGODB_DBNAME = os.getenv("TAX_MONGODB_DBNAME")
# TAX_MONGODB_COLLECTION = os.getenv("TAX_MONGODB_COLLECTION")

def get_db():
    """Connect to MongoDB using env vars."""
    mongodb_uri = os.getenv("MONGO_URI")
    mongodb_db = os.getenv("TAX_MONGODB_DBNAME")
    mongodb_collection = os.getenv("TAX_MONGODB_COLLECTION")

    if not all([mongodb_uri, mongodb_db, mongodb_collection]):
        raise HTTPException(status_code=500, detail="Missing MongoDB environment variables")

    client = AsyncIOMotorClient(mongodb_uri)
    db = client[mongodb_db]
    return db[mongodb_collection]

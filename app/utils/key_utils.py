import secrets
import string
from pymongo import MongoClient
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED
import secrets
from db import keys_collection, db,client
from models import APIKeyModel
from rate_limiter import rate_limit
from utils.constants import API_KEY_NAME
from passlib.hash import bcrypt

# # Connect to MongoDB
# client = MongoClient(MONGO_URI)
# db = client[MONGO_APIKEY_DBNAME]
# keys_collection = db[MONGO_APIKEY_COLLECTION_NAME]

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.verify(plain_password, hashed_password)


# Function to generate a new API key
def generate_api_key(length=32):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

# Validate API key format
def is_valid_apikey(key: str) -> bool:
    return len(key) >= 16 and key.isalnum()

# Check for duplicates in MongoDB
def api_key_exists(key: str) -> bool:
    return keys_collection.find_one({"api_key": key}) is not None


async def validate_api_key_with_rate_limit(api_key: str = Depends(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    record = keys_collection.find_one({"api_key": api_key, "active": True})
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    rate_limit(api_key)  # Make sure this function is correct & doesn’t raise unexpected errors
    return record
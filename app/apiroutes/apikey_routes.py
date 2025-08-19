from fastapi import APIRouter, FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED
import secrets
from models import APIKeyModel, UserCreateModel
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from utils.key_utils import API_KEY_NAME, hash_password,verify_password
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from db import keys_collection
import os

apikey_router = APIRouter()

@apikey_router.post("/delete-key", include_in_schema=(os.environ.get("ENV") == "LOCAL"))
async def delete_key(email: str, password: str):
    # Find the user with an active API key
    existing_key = keys_collection.find_one({"email": email, "active": True})
    if not existing_key:
        raise HTTPException(status_code=404, detail="User has no active API key to delete")

    # Verify password
    if not verify_password(password, existing_key["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Delete key
    keys_collection.delete_one({"_id": existing_key["_id"]})

    return {
        "message": "API key deleted successfully",
        "email": email,
        "api_key": existing_key["api_key"]
    }


@apikey_router.post("/disable-key",include_in_schema=(os.environ.get("ENV") == "LOCAL"))
async def disable_key(email: str, password: str):
    # Find the user with an active API key
    existing_key = keys_collection.find_one({"email": email, "active": True})
    if not existing_key:
        raise HTTPException(status_code=404, detail="User has no active API key to disable")

    # Verify password
    if not verify_password(password, existing_key["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Disable key
    keys_collection.update_one(
        {"_id": existing_key["_id"]},
        {"$set": {"active": False}}
    )

    return {
        "message": "API key disabled successfully",
        "email": email,
        "api_key": existing_key["api_key"]
    }


@apikey_router.post("/enable-key", include_in_schema=(os.environ.get("ENV") == "LOCAL"))
async def enable_key(email: str, password: str):
    # Find the user with an active API key
    existing_key = keys_collection.find_one({"email": email, "active": True})
    if not existing_key:
        raise HTTPException(status_code=404, detail="User has no active API key to enable")

    # Verify password
    if not verify_password(password, existing_key["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Enable key
    keys_collection.update_one(
        {"_id": existing_key["_id"]},
        {"$set": {"active": True}}
    )

    return {
        "message": "API key enabled successfully",
        "email": email,
        "api_key": existing_key["api_key"]
    }


# ---- Generate a new API key ----
@apikey_router.post("/create-key")
# @cross_origin(origins="https://api.accessapis.com")
async def create_key(user: UserCreateModel):
    if user.secret_key != "secret_route_key":
        raise HTTPException(status_code=403, detail="Unauthorized Access")
    else:
        return create_key(user)

def create_key(user: UserCreateModel):
    # Check if user already exists and has an active API key
    existing_key = keys_collection.find_one({"email": user.email, "active": True})
    if existing_key:
        return {
            "message": "User already has an active API key",
            "email": user.email,
            "api_key": existing_key["api_key"]
        }

    # Generate a unique API key
    while True:
        new_key = secrets.token_hex(32)
        if not keys_collection.find_one({"api_key": new_key}):
            break

    # Prepare document
    key_doc = APIKeyModel(
        email=user.email,
        api_key=new_key,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone
    ).dict()

    # Hash and store password separately
    key_doc["password_hash"] = hash_password(user.password)

    try:
        keys_collection.insert_one(key_doc)
    except DuplicateKeyError:
        # Retry once if a race condition happens
        return  create_key(user)

    return {
        "message": "New API key created",
        "email": user.email,
        "api_key": new_key
    }


# Rotate an existing key for the user

@apikey_router.post("/rotate-key", include_in_schema=(os.environ.get("ENV") == "LOCAL"))
# @cross_origin(origins="https://api.accessapis.com")
async def rotate_key(email: str, password: str):
    # Find the user with an active API key
    existing_key = keys_collection.find_one({"email": email, "active": True})
    if not existing_key:
        raise HTTPException(status_code=404, detail="User has no active API key to rotate")

    # Verify password
    if not verify_password(password, existing_key["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Deactivate old key
    keys_collection.update_one(
        {"_id": existing_key["_id"]},
        {"$set": {"active": False, "deactivated_at": datetime.utcnow()}}
    )

    # Generate a new unique API key
    while True:
        new_key = secrets.token_hex(32)
        if not keys_collection.find_one({"api_key": new_key}):
            break

    new_key_doc = {
        "email": existing_key["email"],
        "api_key": new_key,
        "active": True,
        "created_at": datetime.utcnow(),
        "first_name": existing_key["first_name"],
        "last_name": existing_key["last_name"],
        "phone": existing_key["phone"],
        "password_hash": existing_key["password_hash"]  # reuse existing hash
    }

    try:
        keys_collection.insert_one(new_key_doc)
    except DuplicateKeyError:
        # Retry once if a race condition happens
        return await rotate_key(email, password)

    return {
        "message": "API key rotated successfully",
        "email": email,
        "old_key": existing_key["api_key"],
        "new_key": new_key
    }




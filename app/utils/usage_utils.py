from fastapi import Request, Depends
from datetime import datetime
from db import usage_collection
from utils.key_utils import validate_api_key_with_rate_limit

def track_usage(user=Depends(validate_api_key_with_rate_limit), request: Request = None):
    api_key = user["api_key"]
    today = datetime.utcnow().strftime("%Y-%m-%d")

    usage_collection.update_one(
        {"api_key": api_key, "date": today},
        {
            "$inc": {"count": 1, f"endpoints.{request.url.path}": 1},
            "$setOnInsert": {"first_access": datetime.utcnow()},
            "$set": {"last_access": datetime.utcnow()}
        },
        upsert=True
    )
    return user  # Pass user forward to endpoint

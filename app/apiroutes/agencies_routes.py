import os
from fastapi import FastAPI, HTTPException, Query, Depends
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from utils.us_counties import state_counties  # same dict as before
from agencies.agencies_extraction import run_extraction, ExtractionRequest
from utils.mongodb_utils import get_db
from fastapi import APIRouter
from utils.usage_utils import track_usage
from db import keys_collection, usage_collection
from utils.key_utils import API_KEY_NAME, hash_password,verify_password
import os

agencies_router = APIRouter()
load_dotenv()


@agencies_router.post("/get-api-key")
# @cross_origin(origins="https://accessapis.com")
async def get_api_key(email: str, password: str):
    """
    Returns the active API key for a user after verifying email & password.
    """
    # Find active API key for this user
    user_doc = keys_collection.find_one({"email": email, "active": True})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found or no active API key")

    # Verify password
    if not verify_password(password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "message": "API key retrieved successfully",
        "email": email,
        "api_key": user_doc["api_key"],
        "created_at": user_doc.get("created_at"),
        "first_name": user_doc.get("first_name"),
        "last_name": user_doc.get("last_name"),
        "phone": user_doc.get("phone")
    }

@agencies_router.get("/data", include_in_schema=(os.environ.get("ENV") == "LOCAL"))
async def get_data(
    state: Optional[str] = Query(None, description="Filter by state name"),
    county: Optional[str] = Query(None, description="Filter by county name"),
    year: Optional[int] = Query(None, description="Filter by tax year"),
    limit: int = Query(50, ge=1, le=500, description="Max number of results to return"),
    user=Depends(track_usage)
):
    """
    Get extracted tax agency data filtered by state, county, and/or year.
    """
    collection = get_db()

    # Build dynamic query
    query = {}
    if state:
        query["state"] = state
    if county:
        query["county"] = county
    if year:
        query["year"] = year

    # Run query
    cursor = collection.find(query).limit(limit)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
        results.append(doc)

    if not results:
        return {"message": "No matching documents found", "count": 0, "data": []}

    return {"count": len(results), "data": results}


@agencies_router.get("/extract/all", include_in_schema=(os.environ.get("ENV") == "LOCAL"))
async def extract_all(year: int = Query(...), concurrency: int = Query(5), user=Depends(track_usage)):
    return await run_extraction(state_counties, year, concurrency)

@agencies_router.get("/extract/state/{state_name}")
async def extract_state(state_name: str, year: int = Query(...), concurrency: int = Query(5), user=Depends(track_usage)):
    if state_name not in state_counties:
        raise HTTPException(status_code=404, detail="State not found")
    return await run_extraction({state_name: state_counties[state_name]}, year, concurrency)

@agencies_router.get("/extract/state/{state_name}/county/{county_name}")
async def extract_county(state_name: str, county_name: str, year: int = Query(...), concurrency: int = Query(5), user=Depends(track_usage)):
    if state_name not in state_counties or county_name not in state_counties[state_name]:
        raise HTTPException(status_code=404, detail="State or county not found")
    return await run_extraction({state_name: [county_name]}, year, concurrency)

@agencies_router.post("/extract/custom")
async def extract_custom(req: ExtractionRequest, user=Depends(track_usage)):
    if req.counties:
        selected = req.counties
    elif req.states:
        selected = {s: state_counties[s] for s in req.states if s in state_counties}
    else:
        selected = state_counties
    return await run_extraction(selected, req.year, req.concurrency_limit)
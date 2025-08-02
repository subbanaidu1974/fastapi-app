# router.py

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from utils.constants import ALLOWED_DOC_IPS, CENSUS_BASE_URL,CENSUS_URL
from utils.geoapi_utils import check_ip, get_county_fips,get_state_fips, clean_city_name
from datetime import datetime
from db import usage_collection
from utils.usage_utils import track_usage

router = APIRouter()

from fastapi import Query, Depends
from datetime import datetime
from typing import Optional

@router.get("/usage-stats")
async def get_usage_stats(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    user=Depends(track_usage)
):
    """
    Returns daily API usage stats for the current user (per API key).
    Optionally filter by date range.
    """
    query = {"api_key": user["api_key"]}

    # Apply optional date range filters
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["date"] = date_filter

    # Fetch stats from MongoDB
    stats_cursor = usage_collection.find(query, {"_id": 0}).sort("date", -1)
    stats = list(stats_cursor)

    if not stats:
        return {
            "user": user.get("user") or user.get("email"),
            "message": "No usage data found for this period",
            "usage": []
        }

    return {
        "user": user.get("user") or user.get("email"),
        "total_calls": sum(item.get("count", 0) for item in stats),
        "days_tracked": len(stats),
        "usage": stats
    }


@router.get("/secure-data")
async def secure_data(request: Request, user=Depends(track_usage)):
    try:
        return {"message": f"Hello {user['user']}, your API key is valid and within rate limits!"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/state-fips")
async def get_state_fips_all(user=Depends(track_usage)):
    params = {
        "get": "NAME",
        "for": "state:*"
    }
    try:
        response = requests.get(CENSUS_URL, params=params)
        response.raise_for_status()
        data = response.json()

        # First row is header
        header, *rows = data
        result = [{"state_name": row[0], "state_fips": row[1]} for row in rows]

        return {          
            "states": result
        }
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/state-name-by-fips")
async def get_census_data(    
    state: str = Query(..., description="State FIPS code, e.g. 06 for California"), 
    user=Depends(track_usage)
    ):    
    params = {
        "get": ",".join(["NAME"]),
        "for": f"state:{state}"
    }
    response = requests.get(CENSUS_URL, params=params)
    if response.status_code != 200:
        return {"error": response.text}    
    return response.json()
    
@router.get("/state-fips-by-statename")
async def get_state_fips_by_statename(state_name: str = Query(None, description="Full name of the state (e.g. California)"),
                         user=Depends(track_usage)
                         ):
    params = {
        "get": "NAME",
        "for": "state:*"
    }
    try:
        fips = get_state_fips(CENSUS_BASE_URL,state_name)
        response = requests.get(CENSUS_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return [
            {"state_name": state_name, "state_fips": fips}            
        ]        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/state-names")
async def get_state_names(user=Depends(track_usage)):
    try:
        response = requests.get(f"{CENSUS_URL}?get=NAME&for=state:*")
        response.raise_for_status()
        data = response.json()
        _, *rows = data
        state_names = [row[0] for row in rows]
        return state_names
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/counties/{state_name}")
async def get_counties_by_state(state_name: str, user=Depends(track_usage)):
    state_fips = get_state_fips(CENSUS_BASE_URL,state_name)
    print("FIPS CODE ", state_fips)
    if not state_fips:
        raise HTTPException(status_code=404, detail=f"State '{state_name}' not found")
    try:        
        url = f"{CENSUS_BASE_URL}/2020/dec/pl?get=NAME&for=county:*&in=state:{state_fips}"
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        counties = [row[0].replace(f", {state_name.title()}", "") for row in data[1:]]
        return {"state": state_name.title(), "counties": counties}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail="Failed to fetch counties")

@router.get("/cities/{state_name}")
def get_cities_by_state(state_name: str, user=Depends(track_usage)):
    state_fips = get_state_fips(CENSUS_BASE_URL,state_name)
    if not state_fips:
        raise HTTPException(status_code=404, detail="State not found")
    url = f"{CENSUS_BASE_URL}/2020/dec/pl?get=NAME&for=place:*&in=state:{state_fips}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        cities = [row[0].replace(f", {state_name.title()}", "") for row in data[1:]]
        return {"state": state_name,"cities": cities}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cities: {str(e)}")   

@router.get("/county-fips/{state_name}/{county_name}")
def get_county_fips_by_state_and_county(state_name: str, county_name: str, user=Depends(track_usage)):
    state_fips = get_state_fips(CENSUS_BASE_URL,state_name)
    if not state_fips:
        raise HTTPException(status_code=404, detail="State not supported")

    url = f"{CENSUS_BASE_URL}/2020/dec/pl?get=NAME&for=county:*&in=state:{state_fips}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()[1:]  # skip header

        for row in data:
            name, state_code, county_code = row
            if county_name.lower() in name.lower():
                return {
                    "state": state_name,
                    "county": county_name,
                    "county_fips": county_code,
                    "matched_name": name
                }

        raise HTTPException(status_code=404, detail="County not found in the state")

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching county FIPS: {str(e)}")

@router.get("/cities/{state_name}/{county_name}")
async def get_cities_by_county_and_state(
    state_name: str,
    county_name: str,
    user=Depends(track_usage)
):
    """
    Fetch all cities in a given county and state using US Census 2020 API.
    """
    # 1️⃣ Get FIPS codes for state and county
    state_fips, county_fips = get_county_fips(CENSUS_BASE_URL, state_name, county_name)
    if not state_fips or not county_fips:
        raise HTTPException(status_code=404, detail="State or county not found")

    # Debug logs for your container
    print("State FIPS:", state_fips, "| County FIPS:", county_fips)

    url = (
        f"{CENSUS_BASE_URL}/2020/dec/pl"
        f"?get=NAME"
        f"&for=county%20subdivision:*"
        f"&in=state:{state_fips}+county:{county_fips}"
       )

    # 2️⃣ Build the Census API URL
    # url = (
    #     f"{CENSUS_BASE_URL}/2020/dec/pl"
    #     f"?get=NAME&for=place:*&in=state:{state_fips}+county:{county_fips}"
    # )
    print("Fetching Census URL:", url)

    try:
        # 3️⃣ Make the request
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 4️⃣ Parse city names (skip header row)
        raw_cities = [row[0] for row in data[1:]] if len(data) > 1 else []

        # Clean city names
        cities = [clean_city_name(name) for name in raw_cities]

        # 5️⃣ Return clean response
        return {
            "state": state_name,
            "county": county_name,
            "state_fips": state_fips,
            "county_fips": county_fips,
            "total_cities": len(cities),
            "cities": cities
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")



@router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    check_ip(request)
    return get_swagger_ui_html(
        openapi_url=router.openapi_url,
        title=router.title + " - Swagger UI",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        swagger_ui_parameters={"persistAuthorization": False},
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
    )


@router.get("/redoc", include_in_schema=False)
async def custom_redoc_docs(request: Request):
    check_ip(request)
    return get_redoc_html(openapi_url=router.openapi_url, title="Redoc")





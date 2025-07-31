# router.py

from fastapi import APIRouter, Query, HTTPException
from typing import List
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

router = APIRouter()

CENSUS_BASE_URL = "https://api.census.gov/data"
URL_PATH = "/2023/acs/acs5"
CENSUS_URL = CENSUS_BASE_URL + URL_PATH

@router.get("/state-fips")
async def get_state_fips():
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

        return {"states": result}
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/state-name-by-fips")
def get_census_data(    
    state: str = Query(..., description="State FIPS code, e.g. 06 for California")
    ):    
    params = {
        "get": ",".join(["NAME"]),
        "for": f"state:{state}"
    }
    response = requests.get(CENSUS_URL, params=params)
    if response.status_code != 200:
        return {"error": response.text}    
    return response.json()
    
@router.get("/state-fips-by-state")
async def get_state_fips(state_name: str = Query(None, description="Full name of the state (e.g. California)")):
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
async def get_state_names():
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
async def get_counties_by_state(state_name: str):
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
def get_cities_by_state(state_name: str):
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
def get_county_fips(state_name: str, county_name: str):
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
def get_cities_by_county_and_state(state_name: str, county_name: str):    
    state_fips, county_fips = get_county_fips(CENSUS_BASE_URL,state_name,county_name)
    if not county_fips:
        raise HTTPException(status_code=404, detail="county not found")
    url = f"{CENSUS_BASE_URL}/2020/dec/pl?get=NAME&for=place:*&in=state:{state_fips}%20county:{county_fips}"
    # url = f"{CENSUS_BASE_URL}/2020/dec/pl?get=NAME&for=place:*&in=state:{state_fips}+county:{county_fips}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        cities = [row[0] for row in data[1:]]
        return {
            "state": state_name,
            "county": county_name,
            "cities": cities
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

def get_county_fips(baseurl:str,state_name: str, county_name: str):
    base_url = baseurl + "/2020/dec/pl"
    state_fips = get_state_fips(CENSUS_BASE_URL,state_name)
    if not state_fips:
        raise ValueError(f"State not found: {state_name}")
    url = f"{base_url}?get=NAME&for=county:*&in=state:{state_fips}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()[1:]  # Skip header
        for row in data:
            name, state_code, county_code = row
            if county_name.lower() in name.lower():
                return state_fips, county_code
        raise ValueError(f"County '{county_name}' not found in state '{state_name}'")
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch county FIPS: {e}")
    
def get_state_fips(baseurl:str, state_name: str) -> str:
    url = baseurl + "/2020/dec/pl?get=NAME&for=state:*"
    res = requests.get(url)
    data = res.json()
    for row in data[1:]:
        if row[0].lower() == state_name.lower():
            return row[1]
    return None

def get_counties_by_state(baseurl:str,state_name: str):
    state_fips = get_state_fips(state_name)
    if not state_fips:
        raise ValueError("Invalid state name")

    url = baseurl + "/2020/dec/pl?get=NAME&for=county:*&in=state:{state_fips}"
    res = requests.get(url)
    data = res.json()

    counties = [row[0].replace(f", {state_name}", "") for row in data[1:]]
    return {
        "state": state_name,
        "counties": counties
    }
    
    
# Allowed IPs for docs (e.g. localhost only)
ALLOWED_DOC_IPS = {"127.0.0.1", "::1"}

def check_ip(request: Request):
    client_ip = request.client.host
    if client_ip not in ALLOWED_DOC_IPS:
        raise HTTPException(status_code=403, detail="Access forbidden")

@router.get("/docs", include_in_schema=False)
async def custom_swagger_docs(request: Request):
    check_ip(request)
    return get_swagger_ui_html(openapi_url=router.openapi_url, title="Docs")

@router.get("/redoc", include_in_schema=False)
async def custom_redoc_docs(request: Request):
    check_ip(request)
    return get_redoc_html(openapi_url=router.openapi_url, title="Redoc")
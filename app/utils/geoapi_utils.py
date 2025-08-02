
import requests
from fastapi import  Request, HTTPException
from utils.constants import ALLOWED_DOC_IPS, CENSUS_BASE_URL

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
    

def check_ip(request: Request):
    client_ip = request.client.host
    if client_ip not in ALLOWED_DOC_IPS:
        raise HTTPException(status_code=403, detail="Access forbidden")
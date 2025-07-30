from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict
from api.schemas import DataQueryParams, VariableInfo
import requests

router = APIRouter()

BASE_CENSUS_URL = "https://api.census.gov/data"

@router.get("/data/{year}/{dataset}")
async def get_data(year: str, dataset: str, params: DataQueryParams = Depends()):
    # Proxy request
    url = f"{BASE_CENSUS_URL}/{year}/{dataset}"
    resp = requests.get(url, params=params.dict(by_alias=True, exclude_none=True))
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@router.get("/data/{year}/{dataset}/variables.json")
async def get_variables(year: str, dataset: str):
    url = f"{BASE_CENSUS_URL}/{year}/{dataset}/variables.json"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@router.get("/data/{year}/{dataset}/geography.json")
async def get_geography(year: str, dataset: str):
    url = f"{BASE_CENSUS_URL}/{year}/{dataset}/geography.json"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@router.get("/data/{year}/{dataset}/examples.json")
async def get_examples(year: str, dataset: str):
    url = f"{BASE_CENSUS_URL}/{year}/{dataset}/examples.json"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

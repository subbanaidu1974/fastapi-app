import os
import re
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dateutil import parser
from dotenv import load_dotenv
import openai
from utils.us_counties import state_counties  # must be same dict as before
from utils.mongodb_utils import get_db

# Load .env variables
load_dotenv()

# ----- Config -----
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ----- Globals -----
DATE_FIELDS = {
    "firstInstallmentDue", "secondInstallmentDue", "thirdInstallmentDue",
    "delinquencyDate", "delinquencyPenaltyRateOnDate",
    "collectionbillrequest1", "collectionbillrequest2", "collectionbillrequest3"
}

# ----- Utility functions -----
def normalize_date(value):
    if not value or not isinstance(value, str):
        return None
    try:
        dt = parser.parse(value, dayfirst=False)
        return dt.strftime("%m/%d/%Y")
    except Exception:
        return None

def clean_data_fields(data):
    for field in DATE_FIELDS:
        if field in data:
            data[field] = normalize_date(data[field])
    return data

def build_prompt(county, state, year):
    return f"""
Extract the following structured details for the property tax collection agency for {county} County, {state} for the current tax collection year {year}
Format the output as a single valid JSON object.

- All date fields must be formatted as MM/DD/YYYY.
- If any field is not available, return null.
- If multiple payment options exist, include due dates and any discounts or penalties.
- find proper urls for taxwebsite : County tax collection agency website for the current tax collection year
- find the proper website url for assessorwebsite : County assessor website for the current tax collection year

Fields:
{{
  "agencyname": "",
  "agencycode": "",
  "Agencycollects": "",
  "AgencyCollectsdelinquents": "",
  "collector": "",
  "TaxCollectorPhone": "",
  "contactfax": "",
  "contactemail": "",
  "taxwebsite": "",
  "assessorwebsite": "",
  "paytoname": "",
  "paytoaddress": "",
  "paytocity": "",
  "paytostate": "",
  "paytozip": "",
  "numofparcelpercheck": "",
  "acessorcontactnum": "",
  "agencyhasdiscount": "",
  "taxcollectingyear": "",
  "collectionfrequency": "",
  "collectiondiscount1": "",
  "collectionbase1": "",
  "collectionpenalty1": "",
  "collectionbillrequest1": "",
  "collectiondiscount2": "",
  "collectionbase2": "",
  "collectionpenalty2": "",
  "collectionbillrequest2": "",
  "collectiondiscount3": "",
  "collectionbase3": "",
  "collectionpenalty3": "",
  "collectionbillrequest3": "",
  "firstInstallmentDue": "",
  "secondInstallmentDue": "",
  "thirdInstallmentDue": "",
  "delinquencyDate": "",
  "delinquencyPenaltyRateOnDate": ""
}}
"""

def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in response")
    return json.loads(match.group(0))

async def extract_agency(state, county, year, openai_client, mongo_collection, semaphore):
    async with semaphore:
        try:
            prompt = build_prompt(county, state, year)
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You extract structured tax agency data from prompts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            text = response.choices[0].message.content
            data = extract_json(text)
            data.update({"state": state, "county": county})
            clean_data_fields(data)

            if mongo_collection is not None:
                try:
                    await mongo_collection.insert_one(data.copy())
                except Exception as db_error:
                    print(f"DB save failed for {state}, {county}: {db_error}")

            return {"state": state, "county": county, "status": "✅", "data": data}

        except Exception as e:
            return {
                "state": state,
                "county": county,
                "status": "❌",
                "error": str(e),
                "raw_output": locals().get("text", "No response")
            }

async def run_extraction(
    selected_counties: Dict[str, List[str]],
    year: int,
    concurrency_limit: int
):
    openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    mongo_collection = get_db()

    semaphore = asyncio.Semaphore(concurrency_limit)
    tasks = []
    for state, counties in selected_counties.items():
        for county in counties:
            tasks.append(extract_agency(state, county, year, openai_client, mongo_collection, semaphore))

    results = await asyncio.gather(*tasks)
    return results

# ----- API Models -----
class ExtractionRequest(BaseModel):
    year: int
    concurrency_limit: int = 5
    states: Optional[List[str]] = None
    counties: Optional[Dict[str, List[str]]] = None


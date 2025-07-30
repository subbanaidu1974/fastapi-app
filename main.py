from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import httpx
import asyncio
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Geographic Data API",
    description="A FastAPI wrapper for OpenStreetMap Nominatim API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enums for validation
class PlaceType(str, Enum):
    country = "country"
    state = "state"
    county = "county"
    city = "city"
    town = "town"
    village = "village"
    neighbourhood = "neighbourhood"

class OutputFormat(str, Enum):
    json = "json"
    xml = "xml"

# Pydantic models for request/response validation
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200, description="Search query")
    country_codes: Optional[str] = Field(None, regex=r"^[a-z]{2}(,[a-z]{2})*$", description="Country codes (e.g., 'us,ca')")
    limit: Optional[int] = Field(10, ge=1, le=50, description="Maximum number of results")
    accept_language: Optional[str] = Field("en", description="Preferred language")
    addressdetails: Optional[bool] = Field(True, description="Include address details")
    extratags: Optional[bool] = Field(False, description="Include extra tags")
    namedetails: Optional[bool] = Field(False, description="Include name details")

class ReverseRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    zoom: Optional[int] = Field(18, ge=0, le=18, description="Zoom level")
    addressdetails: Optional[bool] = Field(True, description="Include address details")
    accept_language: Optional[str] = Field("en", description="Preferred language")

class AddressComponent(BaseModel):
    house_number: Optional[str] = None
    road: Optional[str] = None
    neighbourhood: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None

class PlaceResponse(BaseModel):
    place_id: Optional[int] = None
    licence: Optional[str] = None
    osm_type: Optional[str] = None
    osm_id: Optional[int] = None
    lat: Optional[str] = None
    lon: Optional[str] = None
    display_name: Optional[str] = None
    address: Optional[AddressComponent] = None
    boundingbox: Optional[List[str]] = None
    importance: Optional[float] = None

# HTTP client with rate limiting
class RateLimitedClient:
    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 1.0  # 1 second between requests for Nominatim

    async def get(self, url: str, params: dict) -> dict:
        # Rate limiting - wait if needed
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        
        self.last_request_time = asyncio.get_event_loop().time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "User-Agent": "FastAPI-Nominatim-Wrapper/1.0 (your-email@example.com)"
            }
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error occurred: {e}")
                raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

# Initialize rate-limited client
nominatim_client = RateLimitedClient()

# API Routes
@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint with API information"""
    return {
        "message": "Geographic Data API powered by OpenStreetMap Nominatim",
        "docs": "/docs",
        "endpoints": {
            "search": "/search",
            "reverse": "/reverse",
            "places_by_type": "/places/{place_type}",
            "health": "/health"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nominatim-wrapper"}

@app.post("/search", response_model=List[PlaceResponse], tags=["Search"])
async def search_places(request: SearchRequest):
    """
    Search for places using text query
    
    - **query**: The place name to search for
    - **country_codes**: Limit search to specific countries (e.g., 'us,ca')
    - **limit**: Maximum number of results (1-50)
    - **addressdetails**: Include detailed address information
    """
    
    params = {
        "q": request.query,
        "format": "json",
        "limit": request.limit,
        "addressdetails": 1 if request.addressdetails else 0,
        "extratags": 1 if request.extratags else 0,
        "namedetails": 1 if request.namedetails else 0,
        "accept-language": request.accept_language
    }
    
    if request.country_codes:
        params["countrycodes"] = request.country_codes
    
    url = "https://nominatim.openstreetmap.org/search"
    data = await nominatim_client.get(url, params)
    
    if not data:
        raise HTTPException(status_code=404, detail="No places found for the given query")
    
    return data

@app.post("/reverse", response_model=PlaceResponse, tags=["Reverse Geocoding"])
async def reverse_geocode(request: ReverseRequest):
    """
    Reverse geocoding - get place information from coordinates
    
    - **lat**: Latitude (-90 to 90)
    - **lon**: Longitude (-180 to 180)
    - **zoom**: Detail level (0-18, higher = more detailed)
    """
    
    params = {
        "lat": request.lat,
        "lon": request.lon,
        "format": "json",
        "zoom": request.zoom,
        "addressdetails": 1 if request.addressdetails else 0,
        "accept-language": request.accept_language
    }
    
    url = "https://nominatim.openstreetmap.org/reverse"
    data = await nominatim_client.get(url, params)
    
    if not data:
        raise HTTPException(status_code=404, detail="No place found for the given coordinates")
    
    return data

@app.get("/places/{place_type}", response_model=List[PlaceResponse], tags=["Places by Type"])
async def get_places_by_type(
    place_type: PlaceType = Path(..., description="Type of place to search for"),
    country: str = Query("US", description="Country code (e.g., 'US', 'CA')"),
    state: Optional[str] = Query(None, description="State/Province name"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Get places by specific type (country, state, county, city, etc.)
    
    - **place_type**: Type of place (country, state, county, city, town, village, neighbourhood)
    - **country**: Country code to search within
    - **state**: Optional state/province to narrow search
    - **limit**: Maximum number of results
    """
    
    # Build search query based on place type
    query_parts = [place_type.value]
    
    if state and place_type != PlaceType.country:
        query_parts.append(state)
    
    if country:
        query_parts.append(country)
    
    query = " ".join(query_parts)
    
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "addressdetails": 1,
        "countrycodes": country.lower() if country else None
    }
    
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    
    url = "https://nominatim.openstreetmap.org/search"
    data = await nominatim_client.get(url, params)
    
    if not data:
        raise HTTPException(
            status_code=404, 
            detail=f"No {place_type.value}s found for the given criteria"
        )
    
    return data

@app.get("/search/advanced", response_model=List[PlaceResponse], tags=["Advanced Search"])
async def advanced_search(
    query: str = Query(..., min_length=2, description="Search query"),
    country_codes: Optional[str] = Query(None, regex=r"^[a-z]{2}(,[a-z]{2})*$", description="Country codes"),
    state: Optional[str] = Query(None, description="State/Province"),
    county: Optional[str] = Query(None, description="County"),
    city: Optional[str] = Query(None, description="City"),
    limit: int = Query(10, ge=1, le=50),
    addressdetails: bool = Query(True),
    dedupe: bool = Query(True, description="Remove duplicate results")
):
    """
    Advanced search with multiple filters
    """
    
    # Build structured query
    query_parts = [query]
    if city:
        query_parts.append(city)
    if county:
        query_parts.append(county)
    if state:
        query_parts.append(state)
    
    structured_query = ", ".join(query_parts)
    
    params = {
        "q": structured_query,
        "format": "json",
        "limit": limit,
        "addressdetails": 1 if addressdetails else 0,
        "dedupe": 1 if dedupe else 0
    }
    
    if country_codes:
        params["countrycodes"] = country_codes
    
    url = "https://nominatim.openstreetmap.org/search"
    data = await nominatim_client.get(url, params)
    
    return data

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )
from fastapi import APIRouter, FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED
import secrets
from apiroutes.apikey_routes import create_key
from models import APIKeyModel, UserCreateModel
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from utils.key_utils import API_KEY_NAME, hash_password,verify_password
from fastapi.openapi.utils import get_openapi
from db import keys_collection, usage_collection
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from apiroutes.agencies_routes import agencies_router
from apiroutes.geo_routes import geo_router
from apiroutes.apikey_routes import apikey_router
import os

origins = {
    "http://localhost:4200",
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "https://api.accessapis.com",
    "https://accessapis.com"
    "http://accessapis.com"
}

app = FastAPI(
    title="My API",
    description="API with API Key authentication in Swagger UI",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": False}  # keeps auth between reloads
)

app.include_router(geo_router,prefix='/api',tags=['General'], include_in_schema=(os.environ.get("ENV") == "LOCAL"))
app.include_router(agencies_router,prefix='/agencies',tags=['Tax Agencies'])
app.include_router(apikey_router,prefix='/apikey',tags=['API Keys'])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["http://localhost:4200"] for tighter security
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP methods
    allow_headers=["*"],  # allow all headers, including x-api-key
)

# CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.on_event("startup")
async def startup_event():
    # Ensure unique index on api_key
    keys_collection.create_index("api_key", unique=True)
    # user = UserCreateModel(email="subbanaidu@yahoo.com", password="admin123", first_name="Admin", last_name="Admin", phone="4445556666", is_admin=True)
    # user: UserCreateModel = new UserCreateModel(email="admin", password="admin", first_name="Admin", last_name="Admin", phone="4445556666", is_admin=True) # type: ignore
    # create_key(user)


# @app.post("/enable-apis")
# async def enable_apis(enable_apis: bool):
#     g_enable_apis = enable_apis
#     return {"message": "APIs enabled successfully"}

# # ---- Add Security for Swagger UI ----
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Add API Key security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": API_KEY_NAME
        }
    }
    # Apply it globally (all endpoints require API key)
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

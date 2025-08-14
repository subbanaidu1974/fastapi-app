from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED
import secrets
from models import APIKeyModel, UserCreateModel
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from utils.key_utils import API_KEY_NAME, hash_password,verify_password
from apiroutes.routes import router
from apiroutes.agencies_routes import agencies_router
from fastapi.openapi.utils import get_openapi
from db import keys_collection, usage_collection
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from flask_cors import CORS
from flask_cors import cross_origin

# API_KEY_NAME = "x-api-key"
# api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


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
app.include_router(router,prefix='/api',tags=['General'])
app.include_router(agencies_router,prefix='/agencies',tags=['Tax Agencies'])
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

from fastapi import Request
from datetime import datetime

# @app.middleware("http")
# async def track_api_usage(request: Request, call_next):
#     # Process the request first
#     response = await call_next(request)

#     # Extract API key
#     api_key = request.headers.get("x-api-key")
#     if api_key:
#         today = datetime.utcnow().strftime("%Y-%m-%d")
#         endpoint = request.url.path

#         # Update MongoDB usage stats
#         usage_collection.update_one(
#             {"api_key": api_key, "date": today},
#             {
#                 "$inc": {"count": 1, f"endpoints.{endpoint}": 1},
#                 "$setOnInsert": {
#                     "first_access": datetime.utcnow(),  # first hit of the day
#                 },
#                 "$set": {
#                     "last_access": datetime.utcnow()    # every request updates last access
#                 }
#             },
#             upsert=True
#         )

#     return response



# ---- Generate a new API key ----


@app.post("/create-key")
# @cross_origin(origins="https://api.accessapis.com")
async def create_key(user: UserCreateModel):
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
        return await create_key(user)

    return {
        "message": "New API key created",
        "email": user.email,
        "api_key": new_key
    }


# Rotate an existing key for the user

@app.post("/rotate-key")
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


@app.post("/get-api-key")
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



app.openapi = custom_openapi

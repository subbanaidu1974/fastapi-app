from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED
import secrets
from models import APIKeyModel
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from utils.key_utils import API_KEY_NAME
from apiroutes.routes import router
from fastapi.openapi.utils import get_openapi
from db import keys_collection

# API_KEY_NAME = "x-api-key"
# api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

app = FastAPI(
    title="My API",
    description="API with API Key authentication in Swagger UI",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": False}  # keeps auth between reloads
)
app.include_router(router,prefix='/api')

@app.on_event("startup")
async def startup_event():
    # Ensure unique index on api_key
    keys_collection.create_index("api_key", unique=True)

# ---- API Key validation ----
# async def validate_api_key_with_rate_limit(api_key: str = Depends(api_key_header)):
#     if not api_key:
#         raise HTTPException(status_code=401, detail="Missing API key")

#     record = keys_collection.find_one({"api_key": api_key, "active": True})
#     if not record:
#         raise HTTPException(status_code=401, detail="Invalid or inactive API key")
#     rate_limit(api_key)  # Make sure this function is correct & doesn’t raise unexpected errors
#     return record


# ---- Generate a new API key ----
@app.post("/create-key")
async def create_key(user: str):
    existing_key = keys_collection.find_one({"user": user, "active": True})
    if existing_key:
        return {
            "message": "User already has an active API key",
            "user": user,
            "api_key": existing_key["api_key"]
        }

    # Generate unique API key
    while True:
        new_key = secrets.token_hex(32)
        if not keys_collection.find_one({"api_key": new_key}):
            break

    key_doc = APIKeyModel(user=user, api_key=new_key).dict()
    try:
        keys_collection.insert_one(key_doc)
    except DuplicateKeyError:
        # Retry once in extremely rare case of race condition
        return await create_key(user)
    
    return {"message": "New API key created", "user": user, "api_key": new_key}

# Rotate an existing key for the user
@app.post("/rotate-key")
async def rotate_key(user: str):
    existing_key = keys_collection.find_one({"user": user, "active": True})
    if not existing_key:
        raise HTTPException(status_code=404, detail="User has no active API key to rotate")

    # Deactivate the old key
    keys_collection.update_one(
        {"_id": existing_key["_id"]},
        {"$set": {"active": False, "deactivated_at": datetime.utcnow()}}
    )

    # Generate a new unique API key
    while True:
        new_key = secrets.token_hex(32)
        if not keys_collection.find_one({"api_key": new_key}):
            break

    new_key_doc = APIKeyModel(user=user, api_key=new_key).dict()
    try:
        keys_collection.insert_one(new_key_doc)
    except DuplicateKeyError:
        # Retry once if duplicate happens due to race condition
        return await rotate_key(user)

    return {
        "message": "API key rotated successfully",
        "user": user,
        "old_key": existing_key["api_key"],
        "new_key": new_key
    } 


# ---- Protected endpoint ----
# @app.get("/secure-data")
# async def secure_data(request: Request, user=Depends(validate_api_key_with_rate_limit)):
#     try:
#         return {"message": f"Hello {user['user']}, your API key is valid and within rate limits!"}
#     except Exception as e:
#         return {"error": str(e)}


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

from fastapi import FastAPI
from api.routes import router as census_router

app = FastAPI(
    title="US Census Bureau Proxy API",
    description="Proxy wrapper based on the MTNA community OpenAPI spec",
    version="1.0.0"
)

app.include_router(census_router, prefix="")

# main.py

from fastapi import FastAPI
from api.routes import router  # import your router

# app = FastAPI(title="Geo Data API's")

app = FastAPI(title="Geo Data API's",docs_url=None, redoc_url=None)

app.include_router(router,prefix='/api')

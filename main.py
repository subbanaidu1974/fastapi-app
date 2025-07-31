# main.py

from fastapi import FastAPI
from api.routes import router  # import your router

app = FastAPI(title="Geo Data API's")

app.include_router(router,prefix='/api')

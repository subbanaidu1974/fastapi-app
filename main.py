# main.py

from fastapi import FastAPI
from api.routes import router  # import your router

app = FastAPI(title="Census API Wrapper")

app.include_router(router,prefix='/api')

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
        return {"message": "FastAPI is live! live! live!. start writing the apis this is to test the api"}


from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
        return {"message": "Hello Testing --- FastAPI is live! live! live!. haaa haaa haaa"}


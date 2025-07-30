from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="AccessAPIs", version="1.0")

# Sample database (in-memory)
fake_db = {}

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Welcome to AccessAPIs"}

@app.get("/items", response_model=List[Item])
def list_items():
    return list(fake_db.values())

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    item = fake_db.get(item_id)
    if item:
        return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", response_model=Item, status_code=201)
def create_item(item: Item):
    if item.id in fake_db:
        raise HTTPException(status_code=400, detail="Item ID already exists")
    fake_db[item.id] = item
    return item

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, updated: Item):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    fake_db[item_id] = updated
    return updated

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id in fake_db:
        del fake_db[item_id]
        return {"detail": "Item deleted"}
    raise HTTPException(status_code=404, detail="Item not found")

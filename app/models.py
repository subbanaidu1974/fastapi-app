from pydantic import BaseModel
from datetime import datetime

class APIKeyModel(BaseModel):
    user: str
    api_key: str
    active: bool = True
    created_at: datetime = datetime.utcnow()

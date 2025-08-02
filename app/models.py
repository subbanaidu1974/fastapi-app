from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreateModel(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str

class APIKeyModel(BaseModel):
    email: EmailStr
    api_key: str
    active: bool = True
    created_at: datetime = datetime.utcnow()
    first_name: str
    last_name: str
    phone: str

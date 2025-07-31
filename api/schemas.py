from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class DataQueryParams(BaseModel):
    get: str
    for_: str = Field(..., alias="for")
    in_: Optional[str] = Field(None, alias="in")
    key: Optional[str] = None

class VariableInfo(BaseModel):
    label: str
    concept: str
    predicateType: Optional[str]
    group: Optional[str]

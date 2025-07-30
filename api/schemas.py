from pydantic import BaseModel
from typing import Optional, Dict, Any

class DataQueryParams(BaseModel):
    get: str
    for_: str  # alias will be used in router
    in_: Optional[str] = None
    key: Optional[str] = None

    class Config:
        fields = {
            'for_': {'alias': 'for'},
            'in_': {'alias': 'in'}
        }

class VariableInfo(BaseModel):
    label: str
    concept: str
    predicateType: Optional[str]
    group: Optional[str]

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field

class Translation(BaseModel):
    value: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str

class TranslationKey(BaseModel):
    id: Optional[str] = None
    key: str
    category: str
    description: Optional[str] = None
    translations: Dict[str, Translation] = Field(default_factory=dict)

class TranslationKeyCreate(BaseModel):
    key: str
    category: str
    description: Optional[str] = None

class TranslationKeyUpdate(BaseModel):
    key: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    translations: Optional[Dict[str, Translation]] = None

class BulkTranslationUpdate(BaseModel):
    translations: Dict[str, Dict[str, str]]  # {key_id: {language_code: value}}
    updated_by: str 
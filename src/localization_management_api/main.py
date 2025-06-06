from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional, Dict
from .models import (
    TranslationKey,
    TranslationKeyCreate,
    TranslationKeyUpdate,
    BulkTranslationUpdate
)
from .database import DatabaseService
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Localization Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP methods
    allow_headers=["*"],
)

## This is the endpoint to get the localizations for a project and locale
## It returns a JSON object with the localizations for the project and locale
@app.get("/localizations/{project_id}/{locale}")
async def get_localizations(project_id: str, locale: str):
    return {"project_id": project_id, "locale": locale, "localizations": {"greeting": "Hello", "farewell": "Goodbye"}}

@app.get("/translation-keys/{key_id}", response_model=TranslationKey)
async def get_translation_key(key_id: str):
    key = await DatabaseService.get_translation_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Translation key not found")
    return key

@app.get("/translation-keys", response_model=List[TranslationKey])
async def list_translation_keys(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=100),
    offset: int = Query(default=0, ge=0)
):
    return await DatabaseService.list_translation_keys(category, search, limit, offset)

@app.post("/translation-keys", response_model=TranslationKey, status_code=201)
async def create_translation_key(key: TranslationKeyCreate):
    return await DatabaseService.create_translation_key(key)

@app.patch("/translation-keys/{key_id}", response_model=TranslationKey)
async def update_translation_key(key_id: str, update: TranslationKeyUpdate):
    key = await DatabaseService.update_translation_key(key_id, update)
    if not key:
        raise HTTPException(status_code=404, detail="Translation key not found")
    return key

@app.delete("/translation-keys/{key_id}", status_code=204)
async def delete_translation_key(key_id: str):
    success = await DatabaseService.delete_translation_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Translation key not found")

@app.post("/translation-keys/bulk-update", status_code=200)
async def bulk_update_translations(update: BulkTranslationUpdate):
    success = await DatabaseService.bulk_update_translations(
        update.translations,
        update.updated_by
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update translations")
    return {"message": "Translations updated successfully"}

@app.get("/translation-keys/stats/completion", response_model=Dict[str, float])
async def get_translation_completion_stats():
    return await DatabaseService.get_translation_completion_stats()

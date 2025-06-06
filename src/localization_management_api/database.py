from supabase import create_client, Client
from typing import List, Optional, Dict, Any
from datetime import datetime
from .config import get_settings
from .models import TranslationKey, TranslationKeyCreate, TranslationKeyUpdate, Translation
from fastapi import HTTPException

settings = get_settings()
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Helper function to serialize datetime objects in a dictionary to ISO 8601 strings
def serialize_datetimes(data: Dict[str, Any]) -> Dict[str, Any]:
    # Create a copy to avoid modifying the original dictionary during iteration
    serialized_data = data.copy()
    for key, value in serialized_data.items():
        if isinstance(value, datetime):
            serialized_data[key] = value.isoformat()
        elif isinstance(value, dict):
            serialized_data[key] = serialize_datetimes(value)
        elif isinstance(value, list):
            serialized_data[key] = [serialize_datetimes(item) if isinstance(item, dict) else item for item in value]
    return serialized_data

# Helper function to parse ISO 8601 strings in a dictionary to datetime objects
def parse_datetimes(data: Dict[str, Any]) -> Dict[str, Any]:
    parsed_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            try:
                # Attempt to parse ISO 8601 string
                # Handle potential timezone information and be flexible with formats
                if value.endswith(('+00:00', 'Z')):
                     # Explicitly handle UTC
                     parsed_data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    # Try parsing with fromisoformat which supports various ISO 8601 formats
                    parsed_data[key] = datetime.fromisoformat(value)
            except ValueError:
                # If not a valid ISO 8601 string, keep as is
                parsed_data[key] = value
        elif isinstance(value, dict):
            parsed_data[key] = parse_datetimes(value)
        elif isinstance(value, list):
             parsed_data[key] = [parse_datetimes(item) if isinstance(item, dict) else item for item in value]
        else:
            parsed_data[key] = value
    return parsed_data

class DatabaseService:
    @staticmethod
    async def get_translation_key(key_id: str) -> Optional[TranslationKey]:
        try:
            response = supabase.table("translation_keys").select("*").eq("id", key_id).execute()
            if not response.data:
                return None
            # Parse datetime strings from Supabase response into datetime objects
            data = parse_datetimes(response.data[0])
            return TranslationKey(**data)
        except Exception as e:
            print(f"Error getting translation key {key_id}: {e}") # Log the original error
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    @staticmethod
    async def list_translation_keys(
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TranslationKey]:
        try:
            query = supabase.table("translation_keys").select("*")
            
            if category:
                query = query.eq("category", category)
            if search:
                query = query.ilike("key", f"%{search}%")
                
            response = query.limit(limit).offset(offset).execute()
            
            keys = []
            for item in response.data:
                # Parse datetime strings from Supabase response
                parsed_item = parse_datetimes(item)
                keys.append(TranslationKey(**parsed_item))

            return keys
        except Exception as e:
            print(f"Error listing translation keys: {e}") # Log the original error
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    @staticmethod
    async def create_translation_key(key: TranslationKeyCreate) -> TranslationKey:
        try:
            # Convert the model to a dict, excluding unset values, and serialize datetimes
            data = key.model_dump(exclude_unset=True)
            # Ensure translations is an empty dict if not provided
            if "translations" not in data or data["translations"] is None:
                data["translations"] = {}
            
            # Serialize datetimes before inserting
            response = supabase.table("translation_keys").insert(serialize_datetimes(data)).execute()
            if not response.data:
                raise HTTPException(status_code=400, detail="Failed to create translation key")
            
            # Parse datetime strings from Supabase response into datetime objects
            created_data = parse_datetimes(response.data[0])
            return TranslationKey(**created_data)
        except Exception as e:
            print(f"Error creating translation key: {e}") # Log the original error
            # Check for unique constraint violation (key already exists)
            if hasattr(e, 'message') and isinstance(e.message, str) and 'duplicate key value violates unique constraint' in e.message:
                 raise HTTPException(status_code=409, detail=f"Translation key '{key.key}' already exists")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    @staticmethod
    async def update_translation_key(key_id: str, update: TranslationKeyUpdate) -> Optional[TranslationKey]:
        try:
            # Convert the update model to a dict, excluding unset values
            data_to_update = update.model_dump(exclude_unset=True)
            
            # Serialize datetime objects within the dictionary before sending
            serialized_data_to_update = serialize_datetimes(data_to_update)

            response = supabase.table("translation_keys").update(serialized_data_to_update).eq("id", key_id).execute()
            
            if not response.data:
                return None
            
            # Parse datetime strings from Supabase response into datetime objects
            updated_data = parse_datetimes(response.data[0])
            return TranslationKey(**updated_data)
        except Exception as e:
            print(f"Error updating translation key {key_id}: {e}") # Log the original error
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    @staticmethod
    async def delete_translation_key(key_id: str) -> bool:
        try:
            response = supabase.table("translation_keys").delete().eq("id", key_id).execute()
            # Supabase delete returns an empty list if successful
            return response.data == []
        except Exception as e:
            print(f"Error deleting translation key {key_id}: {e}") # Log the original error
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    @staticmethod
    async def bulk_update_translations(updates: Dict[str, Dict[str, str]], updated_by: str) -> bool:
        try:
            successful_updates = 0
            for key_id, translations_to_add in updates.items():
                # Fetch the current key using the existing method which handles parsing
                current_key = await DatabaseService.get_translation_key(key_id)
                
                if not current_key:
                    print(f"Warning: Translation key {key_id} not found for bulk update.")
                    continue # Skip this key if not found
                    
                # Get current translations data as a dictionary of dictionaries
                current_translations_data = {} # Initialize as empty dictionary
                if current_key.translations:
                     # Iterate through the Translation models and convert to dictionary, serializing datetime
                    for lang, translation_model in current_key.translations.items():
                         if isinstance(translation_model, Translation): 
                            current_translations_data[lang] = {
                                "value": translation_model.value,
                                "updated_at": translation_model.updated_at.isoformat() if isinstance(translation_model.updated_at, datetime) else translation_model.updated_at,
                                "updated_by": translation_model.updated_by
                            }
                         else:
                             print(f"Warning: Unexpected translation data format for key {key_id}, language {lang}. Expected Translation model.")
                             # If it's not a Translation model, try to include it as is or log/skip
                             # Attempt to serialize if it's a dict containing datetimes
                             current_translations_data[lang] = serialize_datetimes(translation_model) if isinstance(translation_model, dict) else translation_model

                # Merge new translations and add timestamp/updated_by, ensuring ISO format
                updated_translations_data = current_translations_data.copy()
                current_timestamp = datetime.utcnow().isoformat()
                for lang, value in translations_to_add.items():
                    # Ensure the value is treated as a string, although the input type hint is Dict[str, str]
                    updated_translations_data[lang] = {
                        "value": str(value),
                        "updated_at": current_timestamp, # Ensure ISO format
                        "updated_by": updated_by
                    }

                # Prepare update payload - use a simple dict for the nested translations
                # The updated_translations_data should now contain only JSON-serializable values (including string datetimes)
                payload = {"translations": updated_translations_data}

                # Execute the update for this key
                update_response = supabase.table("translation_keys").update(payload).eq("id", key_id).execute()
                
                if update_response.data:
                     successful_updates += 1
                else:
                    print(f"Warning: Failed to update translations for key {key_id} during bulk update.")

            return successful_updates > 0

        except Exception as e:
            print(f"Error during bulk update: {e}") # Log the original error
            raise HTTPException(status_code=500, detail=f"Database error during bulk update: {str(e)}")

    @staticmethod
    async def get_translation_completion_stats() -> Dict[str, float]:
        try:
            # Fetch all translation keys as raw data (dictionaries) to simplify processing
            response = supabase.table("translation_keys").select("translations").execute()
            
            if not response.data:
                return {}
                
            # Get all available languages by looking at all translations
            all_languages = set()
            for item in response.data:
                translations = item.get("translations") # Access translations as a dictionary
                if isinstance(translations, dict):
                    all_languages.update(translations.keys())

            if not all_languages:
                return {}

            # Re-fetch all keys to calculate total count and iterate for stats
            all_keys_response = supabase.table("translation_keys").select("translations").execute()
            all_keys_data = all_keys_response.data if all_keys_response.data else []
            total_keys = len(all_keys_data)

            if total_keys == 0:
                 return {lang: 0.0 for lang in all_languages}
                
            # Count translated keys for each language
            stats = {lang: 0 for lang in all_languages}
            for item in all_keys_data:
                translations = item.get("translations") # Access translations as a dictionary
                if isinstance(translations, dict):
                    for lang in all_languages:
                        # Check if the language exists and has a non-empty value
                        if translations.get(lang) and translations[lang].get("value"):
                            stats[lang] += 1
                
            # Calculate percentages
            completion_stats = {}
            for lang, count in stats.items():
                 completion_stats[lang] = (count / total_keys) * 100
                
            return completion_stats
        except Exception as e:
            print(f"Error getting translation completion stats: {e}") # Log the original error
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 
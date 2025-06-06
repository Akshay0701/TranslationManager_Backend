# Localization Management API

This is a FastAPI application designed to manage localization (translation) keys and their values, interacting with a Supabase PostgreSQL database.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Setup](#setup)
    - [Prerequisites](#prerequisites)
    - [Cloning the Repository](#cloning-the-repository)
    - [Virtual Environment](#virtual-environment)
    - [Installing Dependencies](#installing-dependencies)
- [Database Setup (Supabase)](#database-setup-supabase)
- [Environment Variables (.env)](#environment-variables-env)
- [Running the Application](#running-the-application)
    - [Development Mode (Uvicorn)](#development-mode-uvicorn)
    - [Production Mode (Gunicorn)](#production-mode-gunicorn)
- [API Endpoints](#api-endpoints)
    - [Get Translation Key by ID](#get-translation-key-by-id)
    - [List Translation Keys](#list-translation-keys)
    - [Create Translation Key](#create-translation-key)
    - [Update Translation Key](#update-translation-key)
    - [Delete Translation Key](#delete-translation-key)
    - [Get Translation Completion Stats](#get-translation-completion-stats)

## Tech Stack

- **Backend Framework:** FastAPI
- **Language:** Python 3.12+
- **Database:** Supabase (PostgreSQL)
- **HTTP Server:** Uvicorn
- **Process Manager (Production):** Gunicorn
- **Dependency Management:** Poetry (though `pip` was used for some dependency installations during development)
- **Environment Variables:** python-dotenv / pydantic-settings
- **Database Client:** Supabase Python client

## Setup

### Prerequisites

- Python 3.12 or higher installed.
- Poetry installed (recommended for dependency management, although `pip` can also be used).
- A Supabase account and project set up.

### Cloning the Repository

```bash
git clone <repository_url>
cd localization-management-api
```
(Replace `<repository_url>` with the actual URL of your repository)

### Virtual Environment

It's highly recommended to use a virtual environment.

Using Poetry:

```bash
poetry shell
```

Using `venv` (standard library):

```bash
python3 -m venv venv
source venv/bin/activate # On Windows use `venv\Scripts\activate`
```

### Installing Dependencies

Ensure your virtual environment is activated.

Using Poetry:

```bash
poetry install
```

Using pip:

```bash
pip install -r requirements.txt
pip install supabase python-dotenv pydantic-settings pytest httpx
```
*(Note: During development, we used `pip install` for some packages after initially setting up with Poetry. Ensure all necessary packages are installed in your chosen environment.)*

## Database Setup (Supabase)

1.  Go to your [Supabase project dashboard](https://app.supabase.com/).
2.  Navigate to the **SQL Editor**.
3.  Run the following SQL script to create the `translation_keys` table and set up necessary indexes, RLS, and update triggers:

    ```sql
    -- Create the translation_keys table
    create table if not exists translation_keys (
        id uuid default gen_random_uuid() primary key,
        key text not null unique,
        category text not null,
        description text,
        translations jsonb default '{}'::jsonb,
        created_at timestamp with time zone default timezone('utc'::text, now()) not null,
        updated_at timestamp with time zone default timezone('utc'::text, now()) not null
    );

    -- Create indexes for better performance
    create index if not exists translation_keys_key_idx on translation_keys (key);
    create index if not exists translation_keys_category_idx on translation_keys (category);

    -- Enable Row Level Security (RLS)
    alter table translation_keys enable row level security;

    -- Create a policy that allows all operations (for development)
    create policy "Allow all operations" on translation_keys
        for all
        using (true)
        with check (true);

    -- Create a function to update the updated_at timestamp
    create or replace function update_updated_at_column()
    returns trigger as $$
    begin
        new.updated_at = timezone('utc'::text, now());
        return new;
    end;
    $$ language plpgsql;

    -- Create a trigger to automatically update the updated_at column
    create trigger update_translation_keys_updated_at
        before update on translation_keys
        for each row
        execute function update_updated_at_column();
    ```

## Environment Variables (.env)

Create a file named `.env` in the root directory of the project. Add your Supabase project URL and `anon` API key:

```dotenv
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

Replace `https://your-supabase-url.supabase.co` and `your-supabase-anon-key` with your actual Supabase project details.

## Running the Application

Ensure your virtual environment is activated and you are in the project's root directory.

### Development Mode (Uvicorn)

```bash
uvicorn src.localization_management_api.main:app --reload
```

This will start the server at `http://127.0.0.1:8000` with auto-reloading on code changes. The interactive API documentation (Swagger UI) will be available at `http://127.0.0.1:8000/docs`.

### Production Mode (Gunicorn)

For production, use Gunicorn with Uvicorn workers:

```bash
gunicorn -w 4 -k uvicorn src.localization_management_api.main:app -b 0.0.0.0:8000
```

Replace `4` with the desired number of worker processes (a common rule is `2 * number_of_cores + 1`). The `-b 0.0.0.0:8000` binds the application to all public interfaces on port 8000.

*(Note: As discussed, the `gunicorn -k uvicorn` command might require ensuring `uvicorn` is correctly installed and registered as a worker class in the environment. If you encounter issues, a clean reinstall of `gunicorn` and `uvicorn` or using a standard `systemd` service file configured to use the correct Python interpreter might be necessary.)*

For a full production setup, you would typically run Gunicorn behind a reverse proxy like Nginx or Apache to handle SSL, static files, and listen on standard HTTP/HTTPS ports (80/443).

## API Endpoints

**Base URL:** `http://127.0.0.1:8000`

---

### Get Translation Key by ID

- **HTTP Method:** `GET`
- **Endpoint:** `/translation-keys/{key_id}`
- **Purpose:** Retrieve a single translation key and its associated translations using its unique ID.
- **How to Call:** Send a GET request to the endpoint, replacing `{key_id}` with the actual ID of the translation key you want to retrieve.
- **Example Request:** `GET http://127.0.0.1:8000/translation-keys/your_key_id_here`
- **Expected Response (Success - 200 OK):** Returns a JSON object representing the `TranslationKey` model.

```json
{
    "id": "string (uuid)",
    "key": "string",
    "category": "string",
    "description": "string or null",
    "translations": {
        "language_code": {
            "value": "string",
            "updated_at": "string (ISO 8601 datetime)",
            "updated_by": "string"
        }
        // ... more language codes
    },
    "created_at": "string (ISO 8601 datetime)",
    "updated_at": "string (ISO 8601 datetime)"
}
```

- **Expected Response (Not Found - 404 Not Found):**

```json
{
    "detail": "Translation key not found"
}
```

---

### List Translation Keys

- **HTTP Method:** `GET`
- **Endpoint:** `/translation-keys`
- **Purpose:** Retrieve a list of translation keys. Supports filtering by category and searching by key, as well as pagination.
- **How to Call:** Send a GET request to the endpoint. You can include the following optional query parameters:
    - `category` (string): Filter keys by their category.
    - `search` (string): Search for keys containing the specified string (case-insensitive).
    - `limit` (integer, default=100): Maximum number of results to return.
    - `offset` (integer, default=0): Number of results to skip for pagination.
- **Example Requests:**
    - Get all keys: `GET http://127.0.0.1:8000/translation-keys`
    - Filter by category and search: `GET http://127.0.0.1:8000/translation-keys?category=buttons&search=save`
    - With pagination: `GET http://127.0.0.1:8000/translation-keys?limit=10&offset=20`
- **Expected Response (Success - 200 OK):** Returns a JSON array of `TranslationKey` objects.

```json
[
    {
        "id": "string (uuid)",
        "key": "string",
        "category": "string",
        "description": "string or null",
        "translations": { ... }, // Same structure as above
        "created_at": "string (ISO 8601 datetime)",
        "updated_at": "string (ISO 8601 datetime)"
    }
    // ... more TranslationKey objects
]
```

---

### Create Translation Key

- **HTTP Method:** `POST`
- **Endpoint:** `/translation-keys`
- **Purpose:** Create a new translation key in the database.
- **How to Call:** Send a POST request to the endpoint with a JSON request body representing the new translation key's details.
- **Request Body (Application/json):** Requires `key` and `category`. `description` is optional.

```json
{
    "key": "string (required, must be unique)",
    "category": "string (required)",
    "description": "string or null (optional)"
}
```

- **Example Request Body:**

```json
{
    "key": "homepage.title",
    "category": "titles",
    "description": "The main title on the homepage"
}
```

- **Expected Response (Success - 201 Created):** Returns the newly created `TranslationKey` object, including its generated `id`.

```json
{
    "id": "string (uuid)",
    "key": "string",
    "category": "string",
    "description": "string or null",
    "translations": {}, // Initially empty
    "created_at": "string (ISO 8601 datetime)",
    "updated_at": "string (ISO 8601 datetime)"
}
```
- **Expected Response (Conflict - 409 Conflict):** If a key with the same `key` value already exists.

```json
{
    "detail": "Translation key 'your_key_here' already exists"
}
```

---

### Update Translation Key

- **HTTP Method:** `PATCH`
- **Endpoint:** `/translation-keys/{key_id}`
- **Purpose:** Update an existing translation key. You can update the key, category, description, or add/modify translations.
- **How to Call:** Send a PATCH request to the endpoint, replacing `{key_id}` with the ID of the key to update. Include a JSON request body with the fields you want to modify.
- **Request Body (Application/json):** Contains the fields to update. Include `translations` to add or modify translations for specific languages.

```json
{
    "key": "string (optional)",
    "category": "string (optional)",
    "description": "string or null (optional)",
    "translations": { // optional
        "language_code": { // e.g., "en_US"
            "value": "string (required)",
            "updated_by": "string (required)"
            // updated_at is automatically handled by backend/database trigger
        }
        // ... more language codes
    }
}
```

- **Example Request Body:**

```json
{
    "description": "The main title on the homepage (updated)",
    "translations": {
        "en_US": {
            "value": "Welcome to the App!",
            "updated_by": "frontend_user_1"
        },
        "es_ES": {
            "value": "¡Bienvenido a la aplicación!",
            "updated_by": "frontend_user_1"
        }
    }
}
```

- **Expected Response (Success - 200 OK):** Returns the updated `TranslationKey` object.

```json
{
    "id": "string (uuid)",
    "key": "string",
    "category": "string",
    "description": "string or null",
    "translations": { ... }, // Updated translations
    "created_at": "string (ISO 8601 datetime)",
    "updated_at": "string (ISO 8601 datetime)" // This will be updated by the database trigger
}
```

- **Expected Response (Not Found - 404 Not Found):**

```json
{
    "detail": "Translation key not found"
}
```

---

### Delete Translation Key

- **HTTP Method:** `DELETE`
- **Endpoint:** `/translation-keys/{key_id}`
- **Purpose:** Delete a translation key from the database.
- **How to Call:** Send a DELETE request to the endpoint, replacing `{key_id}` with the ID of the translation key to delete.
- **Example Request:** `DELETE http://127.0.0.1:8000/translation-keys/your_key_id_here`
- **Expected Response (Success - 204 No Content):** The request is successful, and there is no response body.
- **Expected Response (Not Found - 404 Not Found):**

```json
{
    "detail": "Translation key not found"
}
```

---

### Get Translation Completion Stats

- **HTTP Method:** `GET`
- **Endpoint:** `/translation-keys/stats/completion`
- **Purpose:** Get the percentage of translation completion for each language across all translation keys.
- **How to Call:** Send a GET request to the endpoint.
- **Example Request:** `GET http://127.0.0.1:8000/translation-keys/stats/completion`
- **Expected Response (Success - 200 OK):** Returns a JSON object where keys are language codes and values are the completion percentages (float).

```json
{
    "en_US": 95.5,
    "es_ES": 78.0,
    "fr_FR": 60.0,
    "de_DE": 0.0
    // ... more language codes and their percentages
}
```

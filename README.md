# Localization Management API

This is a FastAPI application to manage localizations.

## Setup

1.  Create a virtual environment (optional but recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Running the server

```bash
uvicorn src.localization_management_api.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Example Usage

To get localizations for a project, you can access:
`http://127.0.0.1:8000/localizations/your_project_id/en_US`

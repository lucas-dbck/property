# Property

A full-stack property app in progress. The backend is a FastAPI API for users, property listings, favorites, and inquiries. The frontend scaffold is currently a placeholder and can be replaced or extended with v0 later.

## Backend

The backend lives in `backend/`.

### Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

### Current API surface

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /properties`
- `POST /properties`
- `GET /properties/{property_id}`
- `PATCH /properties/{property_id}`
- `DELETE /properties/{property_id}`
- `POST /properties/{property_id}/images`
- `POST /properties/{property_id}/favorite`
- `DELETE /properties/{property_id}/favorite`
- `POST /inquiries`
- `GET /inquiries/mine`

The local database defaults to SQLite at `backend/property.db`.

### Seed demo data

```bash
cd backend
python -m app.seed
```

Demo login:

- email: `demo@property.local`
- password: `password123`

### Run tests

```bash
cd backend
pytest
```

## Frontend

A lightweight React/Vite placeholder is included for now. It can be replaced with the v0-built frontend once the API contract is settled.

### Run locally

```bash
npm install
npm run dev
```

### Build

```bash
npm run build
```

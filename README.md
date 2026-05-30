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
alembic upgrade head
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
- `GET /opportunities`
- `POST /opportunities`
- `POST /opportunities/imports/immoweb`
- `GET /opportunities/input-template`
- `POST /opportunities/analyze`
- `GET /opportunities/compare`
- `GET /opportunities/{opportunity_id}`
- `GET /opportunities/{opportunity_id}/analysis`
- `PATCH /opportunities/{opportunity_id}`
- `DELETE /opportunities/{opportunity_id}`

The local database defaults to SQLite at `backend/property.db`.

Property listings support sale/rent type, slugs, map coordinates, amenities, availability, energy score, and agent contact fields.

Investment opportunities store imported listing data separately from user overrides, then return a merged `final_data` object for rent estimation and ROI analysis.

Opportunity analysis estimates rent when needed and returns gross yield, net yield, cash flow, cash-on-cash return, and ROI score.

Immoweb import fetches the listing URL and extracts available structured fields into `imported_data`; users can still correct anything through `user_overrides`.

The opportunity input template tells a frontend which ROI fields exist, whether they can be imported, and which values the user should be able to edit.

Quick opportunity analysis lets a frontend calculate ROI from draft inputs before saving an opportunity.

Opportunity comparison ranks saved opportunities by ROI score, cash flow, yield, and cash-on-cash return.

### Environment variables

Copy `backend/.env.example` to your deployment provider or local shell config and set:

- `APP_NAME`: API display name
- `ENVIRONMENT`: `development` or `production`
- `DATABASE_URL`: SQLite locally, Postgres later
- `SECRET_KEY`: long random secret for JWT signing
- `ACCESS_TOKEN_EXPIRE_MINUTES`: login token lifetime
- `CORS_ORIGINS`: comma-separated frontend URLs allowed to call the API

### Database migrations

```bash
cd backend
alembic upgrade head
```

When the models change, create a migration with:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
```

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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes import auth, inquiries, opportunities, properties

settings = get_settings()
settings.validate_for_runtime()

app = FastAPI(
    title=settings.app_name,
    description="Backend API for property listings, users, favorites, and inquiries.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(inquiries.router)
app.include_router(opportunities.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

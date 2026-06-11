from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401
from .config import get_settings
from .database import Base, engine
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


@app.on_event("startup")
def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)
    from .monitoring import start_immoweb_monitor

    start_immoweb_monitor()


app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(inquiries.router)
app.include_router(opportunities.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

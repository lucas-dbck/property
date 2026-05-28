from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth, inquiries, properties

app = FastAPI(
    title="Property API",
    description="Backend API for property listings, users, favorites, and inquiries.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(inquiries.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

import os
from functools import lru_cache


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    app_name: str = os.getenv("APP_NAME", "Property API")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./property.db")
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-before-production")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    cors_origins: list[str] = parse_csv(
        os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def validate_for_runtime(self) -> None:
        if self.is_production and self.secret_key == "change-this-secret-before-production":
            raise RuntimeError("SECRET_KEY must be set in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()

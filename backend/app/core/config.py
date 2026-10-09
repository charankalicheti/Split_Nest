from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Split Money API"
    APP_VERSION: str = "1.0.0"

    DATABASE_URL: str

    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]
        local_origin_pairs = (
            ("http://localhost:5173", "http://127.0.0.1:5173"),
            ("http://127.0.0.1:5173", "http://localhost:5173"),
        )
        for configured_origin, loopback_alias in local_origin_pairs:
            if configured_origin in origins and loopback_alias not in origins:
                origins.append(loopback_alias)
        return origins


settings = Settings()
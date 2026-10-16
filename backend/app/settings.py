from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./tempalquinhohoje.db"
    ADMIN_PASSWORD: str = "changeme"
    # "dev" (default) ou "prod". Em prod desliga /docs e /openapi.json.
    ENVIRONMENT: str = "dev"
    # False em produção (Vercel) pula o init_db no boot — cold start mais rápido.
    # True = cria/migra o schema (default, útil no dev/SQLite e após mudanças de schema).
    run_migrations: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

IS_PROD = settings.ENVIRONMENT.lower() in ("prod", "production")

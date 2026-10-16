from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./tempalquinhohoje.db"
    ADMIN_PASSWORD: str = "changeme"
    # "dev" (default) ou "prod". Em prod desliga /docs e /openapi.json.
    ENVIRONMENT: str = "dev"
    # False em produção (Vercel) pula o init_db no boot — cold start mais rápido.
    # True = cria/migra o schema (default, útil no dev/SQLite e após mudanças de schema).
    run_migrations: bool = True

    # ---- Auto-post do Story no Instagram (cron diário) ----
    # Vazio por default: sem credenciais o cron só loga e não faz nada (não quebra dev).
    # IG_USER_ID: id numérico da conta profissional (@tempalquinhohoje) no Instagram Login.
    # IG_ACCESS_TOKEN: token de longa duração com instagram_business_basic +
    #   instagram_business_content_publish. Renova a cada ~60 dias.
    IG_USER_ID: str = ""
    IG_ACCESS_TOKEN: str = ""
    IG_API_VERSION: str = "v23.0"
    # Segredo do cron: a Vercel manda "Authorization: Bearer $CRON_SECRET" sozinha
    # quando essa env existe. Sem ele, o endpoint fica aberto (só no dev).
    CRON_SECRET: str = ""
    # Base pública usada pra montar a image_url que a Meta busca (precisa ser acessível).
    STORY_BASE_URL: str = "https://tempalquinhohoje.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

IS_PROD = settings.ENVIRONMENT.lower() in ("prod", "production")

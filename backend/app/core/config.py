from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database — verplicht, geen default
    database_url: str = Field(..., description="PostgreSQL async URL (lk_app)")
    database_url_sync: str = Field(..., description="PostgreSQL sync URL (lk_app)")
    platform_database_url: str = Field(..., description="PostgreSQL async URL (lk_platform) — platform-endpoints, ADR-012")

    # Keycloak — verplicht, geen default
    keycloak_url: str = Field(..., description="Keycloak base URL")
    keycloak_realm: str = Field(..., description="Keycloak realm naam")
    keycloak_client_id: str = Field(..., description="Keycloak client ID")
    keycloak_client_secret: str = Field(..., description="Keycloak client secret")
    keycloak_external_url: str = Field("", description="Keycloak URL zoals zichtbaar voor browsers (issuer-validatie)")

    # Keycloak Admin API
    keycloak_admin_user: str = Field("admin", description="Keycloak admin gebruiker")
    keycloak_admin_password: str = Field("changeme_dev", description="Keycloak admin wachtwoord")
    # ADR-029 — dedicated service-account voor user-provisioning (client-credentials, least-privilege)
    likara_provisioning_secret: str = Field("changeme_dev", description="Secret van de likara-user-provisioning service-account")

    # RBAC (ADR-010) — optioneel voorvoegsel op Keycloak-rolnamen.
    # Leeg = canonieke namen (viewer/medewerker/beheerder/auditor) 1-op-1.
    keycloak_role_prefix: str = ""

    # RabbitMQ — verplicht, geen default
    rabbitmq_url: str = Field(..., description="RabbitMQ AMQP URL")

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Cookie — secure=True als productie-default, dev overschrijft via .env
    cookie_name: str = "lk_session"
    refresh_cookie_name: str = "lk_refresh"  # opake sessie-id → refresh_token in Redis (ADR-015)
    cookie_secure: bool = True
    cookie_samesite: str = "strict"
    cookie_domain: str = "localhost"
    access_token_max_age: int = 900    # 15 minuten
    refresh_token_max_age: int = 28800  # 8 uur

    # Security
    platform_origin: str = "http://localhost:3000"
    allowed_redirect_uris: list[str] = ["http://localhost:3000/auth/callback"]

    # OAuth2/OIDC — Authorization Code + PKCE (ADR-002)
    # Leeg = afgeleid van platform_origin (+ /api/v1/auth/callback); configureerbaar via env.
    oidc_redirect_uri: str = ""
    # RP-initiated logout (OP-4). Leeg = afgeleid van platform_origin (+ /login).
    post_logout_redirect_uri: str = ""
    auth_state_ttl: int = 600  # login-state (verifier/nonce/next) in Redis — 10 min

    # Rate limiting
    rate_limit_auth: int = 10
    rate_limit_write: int = 100
    rate_limit_read: int = 300
    rate_limit_admin: int = 50
    rate_limit_window: int = 60

    # Test mode
    likara_test_mode: bool = False
    likara_fixture_set: str = ""

    # MinIO / Blob store (bucket-per-tenant)
    minio_endpoint_url: str = "http://localhost:9000"
    minio_external_url: str = "http://localhost:9000"  # Browser-facing
    minio_root_user: str = "complidata_admin"
    minio_root_password: str = "changeme_dev_only"
    upload_max_bytes: int = 10485760

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()


def validate_startup_config() -> None:
    """Leesbare startup-validatie bij ontbrekende verplichte configuratie."""
    required = {
        "DATABASE_URL": settings.database_url,
        "DATABASE_URL_SYNC": settings.database_url_sync,
        "PLATFORM_DATABASE_URL": settings.platform_database_url,
        "KEYCLOAK_URL": settings.keycloak_url,
        "KEYCLOAK_REALM": settings.keycloak_realm,
        "KEYCLOAK_CLIENT_ID": settings.keycloak_client_id,
        "KEYCLOAK_CLIENT_SECRET": settings.keycloak_client_secret,
        "RABBITMQ_URL": settings.rabbitmq_url,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(
            "\n\n"
            + "=" * 56 + "\n"
            + "  LIKARA — CONFIGURATIEFOUT bij opstarten\n"
            + "=" * 56 + "\n"
            + "  Ontbrekende verplichte omgevingsvariabelen:\n"
            + "".join(f"    - {k}\n" for k in missing)
            + "\n  Zie README.md voor configuratie-instructies.\n"
            + "=" * 56 + "\n"
        )

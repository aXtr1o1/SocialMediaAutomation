from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Social Media Automation API"
    app_env: str = "development"
    app_version: str = "1.0.0"

    supabase_url: str
    supabase_secret_key: SecretStr
    supabase_anon_key: SecretStr = SecretStr("")

    gemini_api_key: SecretStr
    gemini_model: str
    moz_api_key: SecretStr | None = None
    moz_api_url: str = "https://lsapi.seomoz.com/v2/url_metrics"

    secret_key: SecretStr

    linkedin_client_id: str = ""
    linkedin_client_secret: SecretStr = SecretStr("")
    linkedin_redirect_uri: str = ""
    linkedin_scopes: str = "openid profile email w_member_social"

    linkedin_authorization_url: str = (
        "https://www.linkedin.com/oauth/v2/authorization"
    )

    linkedin_token_url: str = (
        "https://www.linkedin.com/oauth/v2/accessToken"
    )

    linkedin_userinfo_url: str = (
        "https://api.linkedin.com/v2/userinfo"
    )

    bluesky_pds_url: str = ""
    bluesky_client_id: str = ""
    bluesky_redirect_uri: str = ""
    bluesky_oauth_scope: str = ""
    bluesky_platform_name: str = "bluesky"

    # Content workflow configuration. No domain/source names are embedded in code.
    workflow_domain_id: str
    source_keyword_weight: float = 0.30
    source_fuzzy_weight: float = 0.20
    source_llm_weight: float = 0.50
    source_relevance_threshold: float = 70.0
    crawler_max_concurrency: int = 5
    crawler_connect_timeout: float = 10.0
    crawler_read_timeout: float = 30.0
    crawler_max_retries: int = 2
    crawler_max_articles_per_source: int = 20
    kpi_pass_threshold: float = 70.0
    kpi_domain_reputation_weight: float = 0.20
    kpi_content_freshness_weight: float = 0.15
    kpi_author_credibility_weight: float = 0.10
    kpi_citation_quality_weight: float = 0.15
    kpi_spam_weight: float = 0.15
    kpi_duplicate_content_weight: float = 0.10
    kpi_website_quality_weight: float = 0.05
    kpi_content_relevance_weight: float = 0.10

    @model_validator(mode="after")
    def validate_weights(self):
        kpi = (self.kpi_domain_reputation_weight + self.kpi_content_freshness_weight +
               self.kpi_author_credibility_weight + self.kpi_citation_quality_weight +
               self.kpi_spam_weight + self.kpi_duplicate_content_weight +
               self.kpi_website_quality_weight + self.kpi_content_relevance_weight)
        matching = self.source_keyword_weight + self.source_fuzzy_weight + self.source_llm_weight
        if abs(kpi - 1.0) > 0.001:
            raise ValueError("KPI weights must sum to 1.0")
        if abs(matching - 1.0) > 0.001:
            raise ValueError("Source relevance weights must sum to 1.0")
        return self

    bluesky_public_api_url: str = (
        "https://public.api.bsky.app"
    )

    bluesky_client_key_id: str | None = None
    bluesky_client_private_key_pem: str | None = None  

    linkedin_platform_name: str = "linkedin"
    bluesky_platform_name: str = "bluesky"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

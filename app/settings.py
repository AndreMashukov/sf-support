from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://support:support@127.0.0.1:5433/support"
    firebase_project_id: str = ""
    firebase_web_api_key: str = ""
    firebase_auth_domain: str = ""
    # Admin SDK (empty means production Auth). Example: 127.0.0.1:9099
    firebase_auth_emulator_host: str = ""
    # Browser JS (empty means production Auth). Example: http://127.0.0.1:9099
    firebase_web_auth_emulator_url: str = ""
    firestore_emulator_host: str = ""
    # Local emulator only: poll supportCommands and skip the Eventarc bus.
    local_cdc_shortcut: bool = False
    support_events_topic: str = "support-events"
    # memory (tests/CLI) or pubsub (Cloud Run)
    support_events_backend: str = "memory"
    # Datastream CDC files land here; Eventarc passes bucket/name to /__eventarc/publish.
    support_cdc_gcs_bucket: str = ""
    gcp_project_id: str = ""
    openrouter_api_key: str = ""
    openrouter_embedding_model: str = "intfloat/multilingual-e5-large"
    openrouter_embeddings_url: str = "https://openrouter.ai/api/v1/embeddings"
    seed_on_startup: bool = False
    together_ai_api_key: str = ""
    together_chat_model: str = "zai-org/GLM-5.2"
    langsmith_project: str = "study-forge-support"
    studyforge_web_url: str = ""


settings = Settings()

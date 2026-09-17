from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://support:support@127.0.0.1:5433/support"
    firebase_project_id: str = ""
    firebase_web_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_embedding_model: str = "intfloat/multilingual-e5-large"
    together_ai_api_key: str = ""
    together_chat_model: str = "zai-org/GLM-5.2"
    langsmith_project: str = "study-forge-support"


settings = Settings()

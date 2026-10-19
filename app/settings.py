from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str = Field(default="http://localhost", env="SUPABASE_URL")
    supabase_key: str = Field(default="dummy_key", env="SUPABASE_KEY")
    jwt_secret: str = Field(default="dummy_secret", env="JWT_SECRET")
    environment: str = Field(default="development", env="ENVIRONMENT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

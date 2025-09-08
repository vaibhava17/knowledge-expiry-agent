import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # AI Configuration
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    default_ai_model: str = os.getenv("DEFAULT_AI_MODEL", "gpt-4-turbo-preview")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    # Database Configuration
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "knowledge_agent")
    mysql_password: Optional[str] = os.getenv("MYSQL_PASSWORD")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "knowledge_expiry")
    
    # Qdrant Configuration
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "knowledge_documents")
    
    # Application Configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "10"))
    
    @property
    def mysql_url(self) -> str:
        return f"mysql+mysqlconnector://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    class Config:
        env_file = ".env"

settings = Settings()
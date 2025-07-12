"""
Configuración del microservicio de IA para reportes
"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Configuración de la aplicación
    APP_NAME: str = "Synap Reports AI Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Configuración de servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Configuración de CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://synap.local",
        "https://app.synap.com"
    ]
    
    # Configuración de autenticación
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Configuración de IA
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"
    
    # Configuración de base de datos vectorial
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION: str = "synap_reports"
    
    # Configuración de logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configuración de rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Configuración de cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Configuración de archivos
    UPLOAD_DIR: str = "/app/uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instancia global de configuración
settings = Settings() 
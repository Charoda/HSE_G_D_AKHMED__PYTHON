
# config.py (обновленный для Render.com PostgreSQL)
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlparse


class Settings(BaseSettings):
    # Для Render.com используем DATABASE_URL
    DATABASE_URL: str
    
    # Telegram Bot Token
    API_TOKEN: str
    
    @property
    def DATABASE_URL_asyncpg(self):
        """Возвращает DATABASE_URL для asyncpg"""
        return self.DATABASE_URL
    
    @property
    def db_params(self):
        """Парсит DATABASE_URL и возвращает параметры"""
        if not self.DATABASE_URL:
            return {}
        
        url = urlparse(self.DATABASE_URL)
        return {
            "host": url.hostname,
            "port": url.port or 5432,
            "database": url.path[1:],  # Убираем первый символ '/'
            "user": url.username,
            "password": url.password
        }
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
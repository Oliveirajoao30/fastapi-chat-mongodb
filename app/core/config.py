"""
Configurações centralizadas da aplicação.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


# Carrega variáveis de ambiente
ROOT_PATH = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_PATH / ".env"

if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)
    print(f"✅ Arquivo .env carregado de: {ENV_FILE}")
else:
    print(f"⚠️ Arquivo .env não encontrado em: {ENV_FILE}")


class Settings:
    """Configurações da aplicação."""
    
    # MongoDB
    MONGO_URL: str = os.getenv("MONGO_URL", "")
    MONGO_DB: str = os.getenv("MONGO_DB", "chatdb")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_CACHE_TTL: int = 86400  # 24 horas
    REDIS_RATE_LIMIT_MAX: int = 30  # mensagens
    REDIS_RATE_LIMIT_WINDOW: int = 60  # segundos
    
    # API
    API_TITLE: str = "Chat API - FastAPI + MongoDB Atlas"
    API_VERSION: str = "2.0.0"
    API_DESCRIPTION: str = """
    ## 🚀 API de Chat em Tempo Real
    
    Sistema de chat com:
    - ✅ WebSocket para mensagens em tempo real
    - ✅ REST API para histórico
    - ✅ MongoDB Atlas para persistência
    - ✅ Validação com Pydantic
    """
    
    # CORS
    CORS_ORIGINS: list = ["*"]  # Em produção, especifique os domínios
    
    # Limites
    MESSAGE_MAX_LENGTH: int = 1000
    USERNAME_MAX_LENGTH: int = 50
    HISTORY_DEFAULT_LIMIT: int = 20
    HISTORY_MAX_LIMIT: int = 100
    
    @property
    def is_configured(self) -> bool:
        """Verifica se as configurações essenciais estão definidas."""
        return bool(self.MONGO_URL)
    
    def validate(self):
        """Valida as configurações."""
        if not self.MONGO_URL:
            raise ValueError(
                "❌ MONGO_URL não está configurada! "
                "Verifique seu arquivo .env"
            )
        
        if not self.MONGO_DB:
            raise ValueError(
                "❌ MONGO_DB não está configurada! "
                "Usando valor padrão: chatdb"
            )
        
        print("✅ Configurações validadas com sucesso!")
        return True


# Instância global das configurações
settings = Settings()
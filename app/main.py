"""
FastAPI Chat Application - Arquivo Principal
Versão refatorada com código modularizado e boas práticas.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from .core.config import settings
from .database.connection import MongoDB
from .routes import messages, websocket


# Gerenciador de ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Conecta ao MongoDB e Redis na inicialização.
    """
    # Startup
    print("🚀 Iniciando aplicação...")
    settings.validate()
    
    # Conecta MongoDB
    await MongoDB.connect(settings.MONGO_URL, settings.MONGO_DB)
    
    # Conecta Redis
    from .database.redis_connection import redis_manager
    await redis_manager.connect(settings.REDIS_URL)
    
    yield  # Aplicação rodando
    
    # Shutdown
    print("🛑 Finalizando aplicação...")
    await redis_manager.disconnect()
    await MongoDB.disconnect()


# Cria instância do FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta arquivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Inclui rotas
app.include_router(messages.router, prefix="/api/v1")
app.include_router(websocket.router)


# Rota principal - serve o cliente HTML
@app.get("/", include_in_schema=False)
async def serve_client():
    """Serve o cliente HTML do chat."""
    return FileResponse("app/static/index.html")


# Rota de health check
@app.get("/health", tags=["monitoring"])
async def health_check():
    """
    Verifica o status da aplicação.
    Útil para monitoramento e deploy.
    """
    from .database.redis_connection import redis_manager
    
    # Testa MongoDB
    try:
        db = MongoDB.get_database()
        await db.command("ping")
        mongo_status = "connected"
    except Exception as e:
        mongo_status = f"error: {str(e)}"
    
    # Testa Redis
    try:
        await redis_manager.redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    # Status geral
    all_connected = mongo_status == "connected" and redis_status == "connected"
    
    return {
        "status": "healthy" if all_connected else "degraded",
        "version": settings.API_VERSION,
        "services": {
            "mongodb": mongo_status,
            "redis": redis_status
        }
    }


# Informações da API
@app.get("/info", tags=["monitoring"])
async def api_info():
    """Retorna informações sobre a API."""
    from .websocket.manager import manager
    
    return {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "active_rooms": manager.get_all_rooms(),
        "total_connections": sum(
            len(users) for users in manager.rooms.values()
        )
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
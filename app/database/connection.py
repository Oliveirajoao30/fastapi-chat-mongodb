"""
Módulo de conexão com MongoDB Atlas.
Centraliza toda a lógica de conexão e operações com o banco de dados.
"""
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime, timezone
import os


class MongoDB:
    """Gerenciador de conexão com MongoDB."""
    
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls, mongo_url: str, db_name: str):
        """
        Conecta ao MongoDB Atlas.
        
        Args:
            mongo_url: String de conexão do MongoDB
            db_name: Nome do banco de dados
        """
        if not mongo_url:
            raise ValueError("MONGO_URL não pode estar vazia!")
        
        cls.client = AsyncIOMotorClient(mongo_url)
        cls.database = cls.client[db_name]
        
        # Testa a conexão
        await cls.client.admin.command('ping')
        print(f"✅ Conectado ao MongoDB! Banco: {db_name}")
    
    @classmethod
    async def disconnect(cls):
        """Desconecta do MongoDB."""
        if cls.client:
            cls.client.close()
            print("❌ Desconectado do MongoDB")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """
        Retorna a instância do banco de dados.
        
        Returns:
            Instância do banco de dados MongoDB
        
        Raises:
            RuntimeError: Se não estiver conectado
        """
        if cls.database is None:
            raise RuntimeError("MongoDB não está conectado! Chame connect() primeiro.")
        return cls.database


# Funções auxiliares para serialização
def serialize_datetime(dt: datetime) -> str:
    """
    Converte datetime para string ISO.
    
    Args:
        dt: Objeto datetime
        
    Returns:
        String no formato ISO
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def serialize_document(doc: dict) -> dict:
    """
    Serializa um documento do MongoDB para JSON.
    
    Args:
        doc: Documento do MongoDB
        
    Returns:
        Dicionário serializado pronto para JSON
    """
    if not doc:
        return doc
    
    result = dict(doc)
    
    # Converte ObjectId para string
    if "_id" in result:
        result["_id"] = str(result["_id"])
    
    # Converte datetime para ISO string
    if "created_at" in result and isinstance(result["created_at"], datetime):
        result["created_at"] = serialize_datetime(result["created_at"])
    
    return result
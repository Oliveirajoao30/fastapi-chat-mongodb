"""
Modelos Pydantic para validação de dados de mensagens.
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class MessageIn(BaseModel):
    """
    Modelo para receber dados de uma nova mensagem.
    Valida os dados antes de salvar no banco.
    """
    username: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Nome do usuário que enviou a mensagem"
    )
    content: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Conteúdo da mensagem"
    )
    
    @field_validator('username')
    def username_not_empty(cls, v: str) -> str:
        """Garante que o username não seja só espaços."""
        v = v.strip()
        if not v:
            raise ValueError('Username não pode ser vazio!')
        return v
    
    @field_validator('content')
    def content_not_empty(cls, v: str) -> str:
        """Garante que o conteúdo não seja só espaços."""
        v = v.strip()
        if not v:
            raise ValueError('Conteúdo não pode ser vazio!')
        return v


class MessageOut(BaseModel):
    """
    Modelo para retornar dados de mensagem.
    Usado nas respostas da API.
    """
    id: str = Field(..., alias="_id", description="ID único da mensagem")
    room: str = Field(..., description="Sala onde a mensagem foi enviada")
    username: str = Field(..., description="Nome do usuário")
    content: str = Field(..., description="Conteúdo da mensagem")
    created_at: str = Field(..., description="Data/hora de criação em ISO format")
    
    class Config:
        """Configurações do modelo."""
        populate_by_name = True  # Permite usar tanto 'id' quanto '_id'


class MessageWebSocket(BaseModel):
    """
    Modelo para mensagens recebidas via WebSocket.
    """
    username: str = Field(default="anon", max_length=50)
    content: str = Field(..., min_length=1, max_length=1000)
    
    @field_validator('content')
    def content_not_empty(cls, v: str) -> str:
        """Garante que o conteúdo não seja só espaços."""
        v = v.strip()
        if not v:
            raise ValueError('Conteúdo não pode ser vazio!')
        return v
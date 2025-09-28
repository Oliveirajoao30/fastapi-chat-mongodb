"""
Rotas REST para operações com mensagens.
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from ..database.connection import MongoDB, serialize_document
from ..models.message import MessageIn, MessageOut


router = APIRouter(
    prefix="/rooms",
    tags=["messages"],
    responses={404: {"description": "Sala não encontrada"}}
)


@router.get("/{room}/messages", response_model=dict)
async def get_messages(
    room: str = Path(..., description="Nome da sala"),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de mensagens"),
    before_id: Optional[str] = Query(None, description="ID para paginação")
):
    """
    Busca mensagens de uma sala específica.
    
    Suporta paginação através do parâmetro before_id.
    """
    db = MongoDB.get_database()
    
    # Monta a query
    query = {"room": room}
    
    # Adiciona filtro de paginação se fornecido
    if before_id:
        try:
            query["_id"] = {"$lt": ObjectId(before_id)}
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail=f"ID inválido: {before_id}"
            )
    
    # Busca mensagens (mais recentes primeiro)
    cursor = db["messages"].find(query).sort("_id", -1).limit(limit)
    
    # Processa resultados
    messages = []
    async for doc in cursor:
        messages.append(serialize_document(doc))
    
    # Inverte para ordem cronológica
    messages.reverse()
    
    # Determina cursor para próxima página
    next_cursor = messages[0]["_id"] if messages else None
    
    return {
        "items": messages,
        "next_cursor": next_cursor,
        "room": room,
        "count": len(messages)
    }


@router.post("/{room}/messages", response_model=MessageOut, status_code=201)
async def create_message(
    room: str = Path(..., description="Nome da sala"),
    message_data: MessageIn = ...
):
    """
    Cria uma nova mensagem em uma sala.
    
    A mensagem é validada antes de ser salva no banco.
    """
    db = MongoDB.get_database()
    
    # Prepara documento para inserir
    doc = {
        "room": room,
        "username": message_data.username.strip()[:50],
        "content": message_data.content.strip()[:1000],
        "created_at": datetime.now(timezone.utc)
    }
    
    # Salva no banco
    result = await db["messages"].insert_one(doc)
    doc["_id"] = result.inserted_id
    
    # Retorna mensagem criada
    return MessageOut(**serialize_document(doc))


@router.delete("/{room}/messages/{message_id}", status_code=204)
async def delete_message(
    room: str = Path(..., description="Nome da sala"),
    message_id: str = Path(..., description="ID da mensagem")
):
    """
    Deleta uma mensagem específica (funcionalidade extra).
    """
    db = MongoDB.get_database()
    
    try:
        object_id = ObjectId(message_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail=f"ID inválido: {message_id}"
        )
    
    # Deleta a mensagem
    result = await db["messages"].delete_one({
        "_id": object_id,
        "room": room
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Mensagem não encontrada"
        )
    
    return None
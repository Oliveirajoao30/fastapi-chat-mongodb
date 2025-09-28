"""
Rotas WebSocket para chat em tempo real.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from pydantic import ValidationError

from ..database.connection import MongoDB, serialize_document
from ..models.message import MessageWebSocket
from ..websocket.manager import manager


router = APIRouter(
    tags=["websocket"]
)


@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """
    Endpoint WebSocket para chat em tempo real.
    
    Protocolo:
    1. Cliente conecta via WebSocket
    2. Servidor envia histórico de mensagens
    3. Cliente envia mensagens em formato JSON
    4. Servidor broadcast para todos na sala
    """
    await manager.connect(room, websocket)
    db = MongoDB.get_database()
    
    try:
        # Envia histórico inicial (últimas 20 mensagens)
        cursor = db["messages"].find({"room": room}).sort("_id", -1).limit(20)
        history = []
        async for doc in cursor:
            history.append(serialize_document(doc))
        
        # Inverte para ordem cronológica
        history.reverse()
        
        # Envia histórico
        await websocket.send_json({
            "type": "history",
            "items": history,
            "room": room
        })
        
        # Loop principal - recebe e processa mensagens
        while True:
            # Recebe dados do cliente
            data = await websocket.receive_json()
            
            # Valida mensagem
            try:
                message = MessageWebSocket(**data)
            except ValidationError as e:
                # Envia erro para o cliente
                await websocket.send_json({
                    "type": "error",
                    "message": "Mensagem inválida",
                    "details": e.errors()
                })
                continue
            
            # Prepara documento para salvar
            doc = {
                "room": room,
                "username": message.username.strip()[:50],
                "content": message.content.strip()[:1000],
                "created_at": datetime.now(timezone.utc)
            }
            
            # Salva no banco
            result = await db["messages"].insert_one(doc)
            doc["_id"] = result.inserted_id
            
            # Broadcast para todos na sala
            await manager.broadcast_message(room, {
                "type": "message",
                "item": serialize_document(doc)
            })
            
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)
        
        # Opcional: notifica outros usuários
        if manager.get_room_count(room) > 0:
            await manager.broadcast_message(room, {
                "type": "user_left",
                "users_count": manager.get_room_count(room)
            })
    
    except Exception as e:
        print(f"❌ Erro no WebSocket: {e}")
        manager.disconnect(room, websocket)
"""
Rotas WebSocket para chat em tempo real com Redis.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from pydantic import ValidationError
import asyncio

from ..database.connection import MongoDB, serialize_document
from ..database.redis_connection import redis_manager
from ..models.message import MessageWebSocket
from ..websocket.manager import manager


router = APIRouter(
    tags=["websocket"]
)


@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """
    Endpoint WebSocket com Redis para melhor performance.
    
    Funcionalidades:
    - Cache de mensagens recentes
    - Pub/Sub para distribuição
    - Presença online
    - Rate limiting
    """
    await manager.connect(room, websocket)
    db = MongoDB.get_database()
    
    # Identifica o usuário (vem na primeira mensagem)
    username = None
    
    try:
        # ========== HISTÓRICO DO CACHE ==========
        # Tenta buscar do Redis primeiro (mais rápido)
        cached_messages = await redis_manager.get_cached_messages(room, limit=20)
        
        if cached_messages:
            # Envia do cache
            await websocket.send_json({
                "type": "history",
                "items": cached_messages,
                "room": room,
                "source": "cache"  # Para debug
            })
        else:
            # Se não tem cache, busca do MongoDB
            cursor = db["messages"].find({"room": room}).sort("_id", -1).limit(20)
            history = []
            async for doc in cursor:
                serialized = serialize_document(doc)
                history.append(serialized)
                # Adiciona no cache para próximas conexões
                await redis_manager.add_message_to_cache(room, serialized)
            
            history.reverse()
            
            await websocket.send_json({
                "type": "history",
                "items": history,
                "room": room,
                "source": "database"  # Para debug
            })
        
        # ========== INSCREVE NO PUB/SUB ==========
        await redis_manager.subscribe_to_room(room)
        
        # Task para escutar mensagens do Redis
        async def listen_redis():
            """Escuta mensagens do canal Redis."""
            while True:
                msg = await redis_manager.get_message_from_pubsub()
                if msg:
                    await websocket.send_json({
                        "type": "message",
                        "item": msg
                    })
                await asyncio.sleep(0.1)
        
        # Inicia task de escuta
        redis_task = asyncio.create_task(listen_redis())
        
        # ========== LOOP DE MENSAGENS ==========
        while True:
            # Recebe dados do cliente
            data = await websocket.receive_json()
            
            # Valida mensagem
            try:
                message = MessageWebSocket(**data)
                
                # Guarda o username na primeira mensagem
                if not username:
                    username = message.username
                    # Marca como online
                    await redis_manager.set_user_online(room, username)
                    
                    # Notifica outros usuários
                    online_users = await redis_manager.get_online_users(room)
                    await manager.broadcast_message(room, {
                        "type": "user_joined",
                        "username": username,
                        "online_users": online_users
                    })
                
            except ValidationError as e:
                await websocket.send_json({
                    "type": "error",
                    "message": "Mensagem inválida",
                    "details": e.errors()
                })
                continue
            
            # ========== RATE LIMITING ==========
            user_id = f"{room}:{username}"
            can_send = await redis_manager.check_rate_limit(
                user_id, 
                max_messages=30,  # 30 mensagens
                window=60  # por minuto
            )
            
            if not can_send:
                await websocket.send_json({
                    "type": "error",
                    "message": "Muitas mensagens! Aguarde um momento."
                })
                continue
            
            # ========== SALVA E DISTRIBUI ==========
            # Prepara documento
            doc = {
                "room": room,
                "username": message.username.strip()[:50],
                "content": message.content.strip()[:1000],
                "created_at": datetime.now(timezone.utc)
            }
            
            # Salva no MongoDB (permanente)
            result = await db["messages"].insert_one(doc)
            doc["_id"] = result.inserted_id
            serialized = serialize_document(doc)
            
            # Adiciona ao cache do Redis
            await redis_manager.add_message_to_cache(room, serialized)
            
            # Publica no Redis pub/sub (distribui para todos)
            await redis_manager.publish_message(room, serialized)
            
            # Também envia direto via WebSocket (fallback)
            await manager.broadcast_message(room, {
                "type": "message",
                "item": serialized
            })
    
    except WebSocketDisconnect:
        # Cancela task do Redis
        if 'redis_task' in locals():
            redis_task.cancel()
        
        # Remove do pub/sub
        await redis_manager.unsubscribe_from_room(room)
        
        # Marca como offline
        if username:
            await redis_manager.set_user_offline(room, username)
            
            # Notifica outros usuários
            online_users = await redis_manager.get_online_users(room)
            await manager.broadcast_message(room, {
                "type": "user_left",
                "username": username,
                "online_users": online_users
            })
        
        # Desconecta WebSocket
        manager.disconnect(room, websocket)
    
    except Exception as e:
        print(f"❌ Erro no WebSocket: {e}")
        
        # Limpa tudo
        if 'redis_task' in locals():
            redis_task.cancel()
        
        await redis_manager.unsubscribe_from_room(room)
        
        if username:
            await redis_manager.set_user_offline(room, username)
        
        manager.disconnect(room, websocket)
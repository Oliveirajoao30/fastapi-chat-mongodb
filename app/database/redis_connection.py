"""
Módulo de conexão com Redis.
Gerencia cache, pub/sub e funcionalidades em tempo real.
"""
import redis.asyncio as redis
from typing import Optional, List, Dict, Any
import json
from datetime import datetime


class RedisManager:
    """Gerenciador de conexão e operações com Redis."""
    
    def __init__(self):
        """Inicializa o gerenciador."""
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        print("🔴 Gerenciador Redis inicializado")
    
    async def connect(self, redis_url: str = "redis://localhost:6379"):
        """
        Conecta ao Redis.
        
        Args:
            redis_url: URL de conexão do Redis
        """
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,  # Retorna strings ao invés de bytes
                health_check_interval=30
            )
            
            # Testa a conexão
            await self.redis_client.ping()
            print(f"✅ Conectado ao Redis: {redis_url}")
            
            # Inicializa pubsub
            self.pubsub = self.redis_client.pubsub()
            
        except Exception as e:
            print(f"❌ Erro ao conectar no Redis: {e}")
            raise
    
    async def disconnect(self):
        """Desconecta do Redis."""
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
            print("❌ Desconectado do Redis")
    
    # ========== CACHE DE MENSAGENS ==========
    
    async def add_message_to_cache(self, room: str, message: dict):
        """
        Adiciona mensagem ao cache (últimas 50).
        
        Args:
            room: Nome da sala
            message: Dicionário com a mensagem
        """
        key = f"chat:{room}:recent"
        
        # Serializa a mensagem para JSON
        message_json = json.dumps(message, default=str)
        
        # Adiciona no início da lista
        await self.redis_client.lpush(key, message_json)
        
        # Mantém apenas as últimas 50
        await self.redis_client.ltrim(key, 0, 49)
        
        # Define expiração de 24 horas
        await self.redis_client.expire(key, 86400)
        
        print(f"💾 Mensagem cacheada na sala '{room}'")
    
    async def get_cached_messages(self, room: str, limit: int = 50) -> List[Dict]:
        """
        Busca mensagens do cache.
        
        Args:
            room: Nome da sala
            limit: Número máximo de mensagens
            
        Returns:
            Lista de mensagens
        """
        key = f"chat:{room}:recent"
        
        # Busca mensagens (0 até limit-1)
        messages_json = await self.redis_client.lrange(key, 0, limit - 1)
        
        # Desserializa cada mensagem
        messages = []
        for msg_json in messages_json:
            try:
                messages.append(json.loads(msg_json))
            except json.JSONDecodeError:
                continue
        
        # Inverte para ordem cronológica (mais antigas primeiro)
        messages.reverse()
        
        print(f"📖 {len(messages)} mensagens recuperadas do cache para sala '{room}'")
        return messages
    
    # ========== PUB/SUB ==========
    
    async def publish_message(self, room: str, message: dict):
        """
        Publica mensagem no canal pub/sub.
        
        Args:
            room: Nome da sala
            message: Mensagem para publicar
        """
        channel = f"chat:{room}"
        message_json = json.dumps(message, default=str)
        
        subscribers = await self.redis_client.publish(channel, message_json)
        print(f"📡 Mensagem publicada para {subscribers} assinantes na sala '{room}'")
    
    async def subscribe_to_room(self, room: str):
        """
        Se inscreve em um canal de sala.
        
        Args:
            room: Nome da sala
        """
        channel = f"chat:{room}"
        await self.pubsub.subscribe(channel)
        print(f"📻 Inscrito no canal '{channel}'")
    
    async def unsubscribe_from_room(self, room: str):
        """
        Remove inscrição de um canal.
        
        Args:
            room: Nome da sala
        """
        channel = f"chat:{room}"
        await self.pubsub.unsubscribe(channel)
        print(f"📴 Desinscrito do canal '{channel}'")
    
    async def get_message_from_pubsub(self):
        """
        Aguarda e retorna próxima mensagem do pub/sub.
        
        Returns:
            Mensagem recebida ou None
        """
        message = await self.pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=1.0
        )
        
        if message and message['type'] == 'message':
            return json.loads(message['data'])
        
        return None
    
    # ========== PRESENÇA ONLINE ==========
    
    async def set_user_online(self, room: str, username: str, ttl: int = 30):
        """
        Marca usuário como online.
        
        Args:
            room: Nome da sala
            username: Nome do usuário
            ttl: Tempo em segundos antes de expirar
        """
        key = f"presence:{room}:{username}"
        await self.redis_client.setex(key, ttl, "online")
        
        # Adiciona no conjunto de usuários online
        set_key = f"online:{room}"
        await self.redis_client.sadd(set_key, username)
        await self.redis_client.expire(set_key, ttl)
        
        print(f"👤 {username} está online na sala '{room}'")
    
    async def set_user_offline(self, room: str, username: str):
        """
        Remove usuário da lista de online.
        
        Args:
            room: Nome da sala
            username: Nome do usuário
        """
        key = f"presence:{room}:{username}"
        await self.redis_client.delete(key)
        
        set_key = f"online:{room}"
        await self.redis_client.srem(set_key, username)
        
        print(f"👻 {username} está offline na sala '{room}'")
    
    async def get_online_users(self, room: str) -> List[str]:
        """
        Lista usuários online em uma sala.
        
        Args:
            room: Nome da sala
            
        Returns:
            Lista de usernames online
        """
        set_key = f"online:{room}"
        users = await self.redis_client.smembers(set_key)
        return list(users)
    
    # ========== RATE LIMITING ==========
    
    async def check_rate_limit(self, user_id: str, max_messages: int = 10, window: int = 60) -> bool:
        """
        Verifica se usuário excedeu limite de mensagens.
        
        Args:
            user_id: Identificador do usuário
            max_messages: Máximo de mensagens permitidas
            window: Janela de tempo em segundos
            
        Returns:
            True se pode enviar, False se excedeu limite
        """
        key = f"rate_limit:{user_id}"
        
        # Incrementa contador
        current = await self.redis_client.incr(key)
        
        # Define expiração na primeira mensagem
        if current == 1:
            await self.redis_client.expire(key, window)
        
        # Verifica se excedeu
        if current > max_messages:
            ttl = await self.redis_client.ttl(key)
            print(f"⛔ Rate limit excedido para {user_id}. Espere {ttl}s")
            return False
        
        print(f"✅ Rate limit OK para {user_id}: {current}/{max_messages}")
        return True


# Instância global
redis_manager = RedisManager()
"""
Gerenciador de conexões WebSocket para o chat.
"""
from typing import Dict, Set
from fastapi import WebSocket
import json


class WebSocketManager:
    """
    Gerencia as conexões WebSocket organizadas por sala.
    Cada sala pode ter múltiplos usuários conectados.
    """
    
    def __init__(self):
        """Inicializa o gerenciador com salas vazias."""
        self.rooms: Dict[str, Set[WebSocket]] = {}
        print("🚀 Gerenciador de WebSocket iniciado!")
    
    async def connect(self, room: str, websocket: WebSocket):
        """
        Conecta um novo usuário a uma sala.
        
        Args:
            room: Nome da sala
            websocket: Conexão WebSocket do usuário
        """
        await websocket.accept()
        
        # Cria a sala se não existir
        if room not in self.rooms:
            self.rooms[room] = set()
            print(f"📦 Nova sala criada: {room}")
        
        # Adiciona o usuário na sala
        self.rooms[room].add(websocket)
        print(f"✅ Usuário conectado na sala '{room}'. Total: {len(self.rooms[room])}")
    
    def disconnect(self, room: str, websocket: WebSocket):
        """
        Desconecta um usuário de uma sala.
        
        Args:
            room: Nome da sala
            websocket: Conexão WebSocket do usuário
        """
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)
            print(f"❌ Usuário desconectado da sala '{room}'. Restantes: {len(self.rooms[room])}")
            
            # Remove a sala se ficar vazia
            if not self.rooms[room]:
                del self.rooms[room]
                print(f"🗑️ Sala '{room}' removida (estava vazia)")
    
    async def broadcast_message(self, room: str, message: dict):
        """
        Envia uma mensagem para todos os usuários de uma sala.
        
        Args:
            room: Nome da sala
            message: Dicionário com a mensagem a enviar
        """
        if room not in self.rooms:
            print(f"⚠️ Tentativa de broadcast em sala inexistente: {room}")
            return
        
        # Lista temporária para evitar modificação durante iteração
        connections = list(self.rooms[room])
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"⚠️ Erro ao enviar mensagem: {e}")
                disconnected.append(websocket)
        
        # Remove conexões que falharam
        for websocket in disconnected:
            self.disconnect(room, websocket)
    
    def get_room_count(self, room: str) -> int:
        """
        Retorna quantos usuários estão em uma sala.
        
        Args:
            room: Nome da sala
            
        Returns:
            Número de usuários na sala
        """
        return len(self.rooms.get(room, set()))
    
    def get_all_rooms(self) -> list:
        """
        Retorna lista de todas as salas ativas.
        
        Returns:
            Lista com nomes das salas e número de usuários
        """
        return [
            {"room": room, "users": len(users)} 
            for room, users in self.rooms.items()
        ]


# Instância global do gerenciador
manager = WebSocketManager()
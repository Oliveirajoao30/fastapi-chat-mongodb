# 🚀 FastAPI Chat + MongoDB Atlas (Versão Refatorada)

Sistema de chat em tempo real desenvolvido com **FastAPI**, **MongoDB Atlas** e **WebSockets**.

## ✨ Características

- 💬 **Chat em tempo real** via WebSocket
- 📦 **MongoDB Atlas** para persistência
- ✅ **Validação de dados** com Pydantic
- 🎯 **Código modularizado** e bem organizado
- 📝 **API REST** para histórico de mensagens
- 🔒 **Tratamento de erros** robusto

## 🚀 Como Executar

### 1. Configurar MongoDB Atlas

1. Crie uma conta em [MongoDB Atlas](https://cloud.mongodb.com)
2. Crie um cluster gratuito
3. Em **Database Access**, crie um usuário
4. Em **Network Access**, adicione seu IP (ou 0.0.0.0/0 para testes)
5. Copie a **connection string**

### 2. Configurar Ambiente
```bash
# Clonar o projeto
git clone [seu-repositorio]
cd [pasta-do-projeto]

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
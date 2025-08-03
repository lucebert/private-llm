from typing import Dict, List, Optional
from contextlib import contextmanager
import os
from pathlib import Path

import chainlit as cl
from llama_cpp import Llama
from sqlalchemy.orm import Session

from database import get_db, ChatMessage, cache_query
from cache import get_cache, set_cache

class ModelConfigurationError(Exception):
    """Raised when model configuration is invalid"""
    pass

def validate_model_path(model_path: str) -> str:
    """Validate that model path exists and is accessible"""
    path = Path(model_path)
    if not path.exists():
        raise ModelConfigurationError(f"Model file not found at {model_path}")
    if not path.is_file():
        raise ModelConfigurationError(f"Model path {model_path} is not a file")
    if not os.access(path, os.R_OK):
        raise ModelConfigurationError(f"Model file {model_path} is not readable")
    return str(path)

def initialize_llm(model_path: str = "./models/7B/llama-2-7b-chat.Q2_K.gguf", 
                n_ctx: int = 2048,
                n_gpu_layers: int = 0) -> Llama:
    """Initialize LLM with validated configuration"""
    validated_path = validate_model_path(model_path)
    
    if n_ctx < 512 or n_ctx > 8192:
        raise ModelConfigurationError(f"Context window {n_ctx} must be between 512 and 8192")
        
    try:
        return Llama(
            model_path=validated_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            use_mlock=True,
            chat_format="llama-2"
        )
    except Exception as e:
        raise ModelConfigurationError(f"Failed to initialize LLM: {str(e)}")

llm = initialize_llm()

async def create_chat_completion(memory: List[str]):
    return llm.create_chat_completion(
        stream=True,
        messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant",
        },
        *memory
    ],
    response_format={
        "type": "text"
    },
    temperature=0,
)

@cl.on_chat_start
async def on_chat_start():
    memory = []
    cl.user_session.set("memory", memory)

@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="", author="Assistant")
    memory = update_memory("user", message.content)
    output = await create_chat_completion(memory)
    response = ""
    for chunk in output:
        delta = chunk['choices'][0]['delta']
        if 'content' in delta:
            response += delta['content']
            await msg.stream_token(delta['content'])

    update_memory("assistant", response)
    await msg.send()


def validate_message(role: str, content: str) -> None:
    """Validate chat message parameters"""
    valid_roles = {"user", "assistant", "system"}
    if role not in valid_roles:
        raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
    if not content or not isinstance(content, str):
        raise ValueError("Message content must be a non-empty string")
    if len(content) > 4096:  # Reasonable max length
        raise ValueError("Message content exceeds maximum length of 4096 characters")

@cache_query(ttl=60)
def get_recent_messages(db: Session, limit: int = 10) -> List[ChatMessage]:
    """Get recent messages with caching"""
    return db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(limit).all()

def update_memory(role: str, content: str) -> List[Dict[str, str]]:
    """ Handle conversation memory with database persistence, pooling and caching """
    validate_message(role, content)
    
    session_id = cl.user_session.get("session_id", "default")
    if not session_id:
        raise ValueError("Invalid session ID")
        
    cache_key = f"memory:{session_id}"
    
    # Try to get memory from cache first
    memory = get_cache(cache_key)
    if memory is None:
        memory = cl.user_session.get("memory")
        if not isinstance(memory, list):
            memory = []  # Reset if invalid
            
    memory.append({"role": role, "content": content})
    
    # Persist message to database using connection pool with improved error handling and batch operations
    with get_db() as db:
        try:
            # Use bulk insert for better performance
            truncated_content = content[:150] if role == "assistant" else content
            db_message = ChatMessage(role=role, content=truncated_content)
            db.bulk_save_objects([db_message])
            db.commit()
            
            # Update cached recent messages
            get_recent_messages.cache_clear() if hasattr(get_recent_messages, 'cache_clear') else None
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist messages: {e}")
            raise

    # Update cache and session memory
    memory = memory[-2:]  # Keep only last 2 messages
    if not set_cache(cache_key, memory, 3600):  # Cache for 1 hour
        cl.user_session.set("memory", memory)  # Fallback to session if cache fails
    else:
        cl.user_session.set("memory", memory)
    return memory

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)

from typing import Dict, List
from contextlib import contextmanager

import chainlit as cl
from llama_cpp import Llama
from sqlalchemy.orm import Session

from database import get_db, ChatMessage
from cache import get_cache, set_cache

llm = Llama(
        model_path="./models/7B/llama-2-7b-chat.Q2_K.gguf",  # Path to the model.
        # n_gpu_layers=-1,  # Default is 0 means use CPU
        # use_mlock=True,  # Force the system to keep the model in RAM.
        # seed=1337,  # Uncomment to set a specific seed
        # n_ctx=2048,  # Uncomment to increase the context window
        # chat_format="llama-2"  # String specifying the chat format to use
    )

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


def update_memory(role: str, content: str) -> List[Dict[str, str]]:
    """ Handle conversation memory with database persistence, pooling and caching """
    session_id = cl.user_session.get("session_id", "default")
    cache_key = f"memory:{session_id}"
    
    # Try to get memory from cache first
    memory = get_cache(cache_key) or cl.user_session.get("memory")
    memory.append({"role": role, "content": content})
    
    # Persist message to database using connection pool
    db = next(get_db())
    try:
        db_message = ChatMessage(role=role, content=content[:150] if role == "assistant" else content)
        db.add(db_message)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    # Update cache and session memory
    memory = memory[-2:]  # Keep only last 2 messages
    set_cache(cache_key, memory, 3600)  # Cache for 1 hour
    cl.user_session.set("memory", memory)
    return memory

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)

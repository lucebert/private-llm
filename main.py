from typing import Dict, List

import chainlit as cl
from llama_cpp import Llama

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
    """ Handle small memory by keeping only the last 2 messages and truncating assistant's response"""
    memory = cl.user_session.get("memory")
    memory.append({"role": role, "content": content})
    if role == "assistant":
        content = content[:150]  # Truncate assistant's response to 150 characters
    cl.user_session.set("memory", memory[-2:])  # Keep only the last 2 messages
    return memory

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)

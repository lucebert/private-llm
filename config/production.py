config = {
    "env": "production",
    "debug": False,
    "model": {
        "model_path": "/opt/models/llama-2-7b-chat.Q2_K.gguf",
        "n_ctx": 4096,
        "n_gpu_layers": 32,
        "use_mlock": True,
        "chat_format": "llama-2"
    },
    "cache": {
        "enabled": True,
        "ttl": 7200,
        "max_size": 10000
    },
    "database": {
        "url": "postgresql://user:pass@localhost:5432/chatdb",
        "pool_size": 20,
        "max_overflow": 30,
        "pool_timeout": 60,
        "pool_recycle": 3600
    },
    "log_level": "INFO"
}
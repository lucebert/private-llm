config = {
    "env": "development",
    "debug": True,
    "model": {
        "model_path": "./models/7B/llama-2-7b-chat.Q2_K.gguf",
        "n_ctx": 2048,
        "n_gpu_layers": 0,
        "use_mlock": True,
        "chat_format": "llama-2"
    },
    "cache": {
        "enabled": True,
        "ttl": 3600,
        "max_size": 1000
    },
    "database": {
        "url": "sqlite:///chat.db",
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 3600
    },
    "log_level": "DEBUG"
}
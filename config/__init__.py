from pathlib import Path
from typing import Dict, Optional
import os
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    model_path: str = Field(default="./models/7B/llama-2-7b-chat.Q2_K.gguf")
    n_ctx: int = Field(default=2048, ge=512, le=8192)
    n_gpu_layers: int = Field(default=0, ge=0)
    use_mlock: bool = Field(default=True)
    chat_format: str = Field(default="llama-2")

class CacheConfig(BaseModel):
    enabled: bool = Field(default=True)
    ttl: int = Field(default=3600)
    max_size: int = Field(default=1000)

class DatabaseConfig(BaseModel):
    url: str = Field(default="sqlite:///chat.db")
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=3600)

class Config(BaseModel):
    env: str = Field(default="development")
    debug: bool = Field(default=False)
    model: ModelConfig = Field(default_factory=ModelConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    log_level: str = Field(default="INFO")

    @classmethod
    def load(cls, env: Optional[str] = None) -> "Config":
        if env is None:
            env = os.getenv("APP_ENV", "development")
            
        config_dir = Path(__file__).parent
        config_file = config_dir / f"{env}.py"
        
        if not config_file.exists():
            raise ValueError(f"Config file for environment {env} not found")
            
        config_dict = {}
        exec(config_file.read_text(), {}, config_dict)
        return cls(**config_dict.get("config", {}))
import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

def load_config() -> dict:
    """从环境变量和 Agent/.env 文件加载配置"""
    agent_dir = Path(__file__).resolve().parent
    env_path = agent_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        load_dotenv()

    api_key: Optional[str] = os.getenv("QWEN_API_KEY")
    access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID")
    access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
    base_url: str = os.getenv(
        "QWEN_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    model: str = os.getenv("QWEN_MODEL", "qwen-plus")
    region_id: str = os.getenv("ALIYUN_REGION", "cn-hangzhou")

    if not api_key:
        raise RuntimeError("缺少 QWEN_API_KEY，请在系统环境或 .env 中配置。")
    if not access_key_id or not access_key_secret:
        raise RuntimeError("缺少阿里云访问密钥，请在系统环境或 .env 中配置。")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "access_key_id": access_key_id,
        "access_key_secret": access_key_secret,
        "region_id": region_id,
    }
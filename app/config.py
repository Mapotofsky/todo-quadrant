"""AI 接口配置读写。"""
import os

from app import db

AI_BASE_URL_KEY = "ai_base_url"
AI_API_KEY_KEY = "ai_api_key"
AI_MODEL_KEY = "ai_model"
AI_PROMPT_KEY = "ai_system_prompt"

DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2.6-flash"


def get_ai_config():
    return {
        "base_url": db.get_setting(AI_BASE_URL_KEY, "") or DEFAULT_BASE_URL,
        "api_key": db.get_setting(AI_API_KEY_KEY, "") or "",
        "model": db.get_setting(AI_MODEL_KEY, "") or DEFAULT_MODEL,
        "system_prompt": db.get_setting(AI_PROMPT_KEY, "") or "",
    }


def set_ai_config(base_url, api_key, model):
    db.set_setting(AI_BASE_URL_KEY, (base_url or "").strip())
    db.set_setting(AI_API_KEY_KEY, (api_key or "").strip())
    db.set_setting(AI_MODEL_KEY, (model or "").strip())


def auto_load_api_key(project_root):
    """若尚未配置 key，且项目根存在 api-key.txt，则读取并写入设置（不打印内容）。"""
    if db.get_setting(AI_API_KEY_KEY, ""):
        return
    path = os.path.join(project_root, "api-key.txt")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            key = f.read().strip()
    except OSError:
        return
    if key:
        db.set_setting(AI_API_KEY_KEY, key)

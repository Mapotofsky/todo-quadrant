"""OpenAI 兼容接口调用 + 健壮 JSON 解析（Python 标准库 urllib）。"""
import json
import re
import urllib.request

DEFAULT_SYSTEM_PROMPT = (
    "你是任务提炼助手。把用户粘贴的聊天/文本提炼成一条待办任务，只输出 JSON："
    '{"title":"不超过20字的任务标题","note":"一句话补充(可空字符串)",'
    '"important":true或false,"urgent":true或false,"due_at":"YYYY-MM-DD HH:MM"或null}。'
    "不要输出任何其它内容。"
)


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "是", "重要", "紧急", "高")
    return bool(v)


def parse_content(content):
    """从模型输出中健壮地解析任务 JSON；失败则降级为纯文本标题。"""
    text = (content or "").strip()
    data = None
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                data = None
    if not isinstance(data, dict):
        return {
            "title": text[:100] or "未命名任务",
            "note": "",
            "important": False,
            "urgent": False,
            "due_at": None,
        }
    title = str(data.get("title") or "").strip() or text[:100] or "未命名任务"
    note = str(data.get("note") or "").strip()
    due_at = data.get("due_at")
    if due_at in (None, ""):
        due_at = None
    else:
        due_at = str(due_at).strip()
    return {
        "title": title[:200],
        "note": note,
        "important": _to_bool(data.get("important")),
        "urgent": _to_bool(data.get("urgent")),
        "due_at": due_at,
    }


def summarize(text, base_url, api_key, model, system_prompt="", timeout=30):
    """调用 chat/completions 并解析。失败抛异常，由调用方处理。"""
    url = (base_url or "").rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + (api_key or ""))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    obj = json.loads(body)
    content = obj["choices"][0]["message"]["content"]
    return parse_content(content)

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import AIModel, AIProviderSetting


class AICommandError(Exception):
    pass


NON_CHAT_MODEL_KEYWORDS = (
    "audio",
    "babbage",
    "davinci",
    "dall-e",
    "edit",
    "embedding",
    "image",
    "instruct",
    "moderation",
    "realtime",
    "search",
    "tts",
    "transcribe",
    "translation",
    "whisper",
)
CHAT_MODEL_PREFIXES = ("gpt-", "chat-", "chatgpt-", "o1", "o3", "o4")
PREFERRED_CHAT_MODELS = (
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4o-mini",
    "gpt-4o",
    "chat-latest",
    "gpt-3.5-turbo",
)


def model_requires_default_temperature(model_id):
    normalized = (model_id or "").lower()
    return normalized.startswith("gpt-5")


def with_supported_generation_params(payload, temperature=None, max_tokens=None):
    model_id = payload.get("model", "")
    if temperature is not None and not model_requires_default_temperature(model_id):
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    return payload


def is_ollama_setting(setting):
    provider = (setting.provider or "").lower()
    base_url = (setting.base_url or "").lower()
    return "ollama" in provider or "localhost:11434" in base_url or "127.0.0.1:11434" in base_url


def is_chat_completion_model(model_id, setting=None):
    normalized = (model_id or "").lower()
    if not normalized:
        return False
    if setting and is_ollama_setting(setting):
        return not any(keyword in normalized for keyword in ("embed", "embedding"))
    if any(keyword in normalized for keyword in NON_CHAT_MODEL_KEYWORDS):
        return False
    return normalized.startswith(CHAT_MODEL_PREFIXES)


def choose_chat_model(setting):
    if is_chat_completion_model(setting.model, setting):
        return setting.model

    active_model_ids = list(
        setting.models.filter(is_active=True).values_list("model_id", flat=True)
    )
    for preferred in PREFERRED_CHAT_MODELS:
        if preferred in active_model_ids:
            return preferred
    for model_id in active_model_ids:
        if is_chat_completion_model(model_id, setting):
            return model_id
    return ""


def build_reference_context(sources, files):
    lines = []
    for source in sources:
        lines.append(f"- 來源：{source.title}")
        if source.url:
            lines.append(f"  URL：{source.url}")
        if source.citation_note:
            lines.append(f"  引用資訊：{source.citation_note}")
    for reference_file in files:
        lines.append(f"- 檔案：{reference_file.title}")
        if reference_file.source:
            lines.append(f"  關聯來源：{reference_file.source.title}")
        lines.append(f"  檔案路徑：{reference_file.file.name}")
    return "\n".join(lines)


def api_base_url(setting):
    return (setting.base_url or "https://api.openai.com/v1").rstrip("/")


def api_request(setting, path, payload=None, timeout=60):
    if not setting or not setting.api_key:
        raise AICommandError("尚未在設定頁填入 AI API Key。")
    return api_request_with_config(setting.base_url, setting.api_key, path, payload=payload, timeout=timeout)


def api_request_with_config(base_url, api_key, path, payload=None, timeout=60):
    if not api_key:
        raise AICommandError("尚未填入 AI API Key。")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{(base_url or 'https://api.openai.com/v1').rstrip('/')}{path}",
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AICommandError(f"AI API 回應錯誤 HTTP {exc.code}: {detail[:500]}") from exc
    except URLError as exc:
        raise AICommandError(f"無法連線到 AI API：{exc.reason}") from exc
    except TimeoutError as exc:
        raise AICommandError("AI API 請求逾時。") from exc


def fetch_available_model_ids(base_url, api_key):
    data = api_request_with_config(base_url, api_key, "/models", timeout=30)
    return [item["id"] for item in data.get("data", []) if item.get("id")]


def load_available_models(setting):
    model_ids = fetch_available_model_ids(setting.base_url, setting.api_key)
    loaded = 0
    seen = set()
    for model_id in model_ids:
        seen.add(model_id)
        AIModel.objects.update_or_create(
            api_setting=setting,
            model_id=model_id,
            defaults={"display_name": model_id, "is_active": True},
        )
        loaded += 1
    if seen:
        setting.models.exclude(model_id__in=seen).update(is_active=False)
    return loaded


def test_ai_setting(setting):
    model = choose_chat_model(setting)
    if not model:
        raise AICommandError("尚未設定或載入可用的對話模型。請先按「載入 Model」，或設定 gpt-4.1-mini 等 chat model。")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "請用繁體中文簡短回覆。"},
            {"role": "user", "content": "請回覆：設定測試成功"},
        ],
    }
    payload = with_supported_generation_params(payload, temperature=0, max_tokens=32)
    data = api_request(setting, "/chat/completions", payload=payload, timeout=30)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise AICommandError("AI API 測試回應格式無法解析。") from exc


def run_ai_command(prompt, api_setting, model, sources, files, allow_database_changes=False, question_context=""):
    setting = api_setting
    reference_context = build_reference_context(sources, files)
    context_sections = []
    if reference_context:
        context_sections.append(f"參考來源：\n{reference_context}")
    if question_context:
        context_sections.append(f"題庫資料表：\n{question_context}")
    if context_sections:
        user_content = (
            "\n\n".join(context_sections)
            + "\n\n使用者指令：\n"
            + prompt
            + "\n\n請直接依照上方資料完成使用者指令，輸出實際內容。"
            + "不要只回答 Excellent、OK、收到、可以，或其他確認語。"
        )
    else:
        user_content = (
            prompt
            + "\n\n請直接完成使用者指令，輸出實際內容。"
            + "不要只回答 Excellent、OK、收到、可以，或其他確認語。"
        )

    system_content = "你是協助命題與審題的助理。請使用繁體中文，產出可直接供題庫編輯者檢視的內容。"
    if allow_database_changes:
        system_content = (
            "你是可協助操作題庫資料庫的命題助理。若使用者要求修改資料庫，"
            "請只輸出 JSON，不要輸出其他文字。格式為："
            '{"actions":[{"action":"create_question","fields":{"stem":"題幹","choice_a":"...","choice_b":"...","choice_c":"...","choice_d":"...","answer":"A","revised_explanation":"解析"}},'
            '{"action":"update_question","id":1,"fields":{"revised_explanation":"..."}},'
            '{"action":"mark_completed","id":1}]}。'
            "可用 action 只有 create_question、update_question、mark_completed。"
            "若只是一般諮詢，請用繁體中文回答。"
        )
    else:
        system_content += (
            "若使用者要求列出、分析、審查或整理題庫，請根據提供的題庫資料表逐項回答，"
            "必要時列出題目 ID 與題幹。不要只用簡短讚許或確認語回覆。"
        )
    payload = {
        "model": model.model_id if hasattr(model, "model_id") else model or setting.model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    }
    if not payload["model"]:
        raise AICommandError("請先選擇或設定可使用的模型。")
    payload = with_supported_generation_params(payload, temperature=0.4)

    data = api_request(setting, "/chat/completions", payload=payload, timeout=60)

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise AICommandError("AI API 回應格式無法解析。") from exc

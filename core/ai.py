"""Lớp gọi AI dùng chung: Claude (Anthropic SDK), OpenAI, Gemini và gateway nội bộ (OpenAI-compatible).

AI chỉ làm phần cần "hiểu" (map tên item, đọc ghi chú tự do, viết tóm tắt). Logic đối chiếu chính
nằm trong code để kết quả ổn định và kiểm chứng được.
"""
from __future__ import annotations

import json
import re

from . import config
from .i18n import t

PROVIDERS = {
    "claude": {"label": "Claude (Anthropic)", "model": "claude-opus-5-5"},
    "openai": {"label": "OpenAI (GPT)", "model": "gpt-5"},
    "gemini": {
        "label": "Gemini (Google)",
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    "gateway": {"label": "Gateway nội bộ (OpenAI-compatible)", "model": ""},
}


class AIError(RuntimeError):
    pass


def is_configured(settings: dict | None = None) -> tuple[bool, str]:
    settings = settings or config.load_settings()
    provider = settings["ai"]["provider"]
    label = t(PROVIDERS.get(provider, {}).get("label", provider))
    if not config.api_key(settings, provider):
        return False, t("Chưa có API key cho {label}", label=label)
    if provider == "gateway" and not settings["ai"]["gateway"].get("base_url"):
        return False, t("Gateway nội bộ chưa có base URL")
    return True, label


class AIClient:
    def __init__(self, settings: dict | None = None, provider: str | None = None, require_model: bool = True):
        self.settings = settings or config.load_settings()
        self.provider = provider or self.settings["ai"]["provider"]
        if self.provider not in PROVIDERS:
            raise AIError(t("Provider không hợp lệ: {provider}", provider=self.provider))
        conf = self.settings["ai"].get(self.provider, {})
        self.label = t(PROVIDERS[self.provider]["label"])
        self.model = (conf.get("model") or PROVIDERS[self.provider]["model"]).strip()
        self.api_key = config.api_key(self.settings, self.provider)
        self.base_url = conf.get("base_url") or PROVIDERS[self.provider].get("base_url")
        if not self.api_key:
            raise AIError(t("Chưa có API key cho {label}. Vào trang Cài đặt để nhập.", label=self.label))
        if require_model and not self.model:
            raise AIError(t("Chưa chọn model cho {label}.", label=self.label))
        if self.provider == "gateway" and not self.base_url:
            raise AIError(t("Gateway nội bộ chưa có base URL."))

    # ---- API công khai -------------------------------------------------
    def text(self, system: str, prompt: str, effort: str = "medium") -> str:
        if self.provider == "claude":
            return self._claude(system, prompt, None, effort)
        return self._openai_compatible(system, prompt, None)

    def json(self, system: str, prompt: str, schema: dict, effort: str = "low") -> dict:
        if self.provider == "claude":
            raw = self._claude(system, prompt, schema, effort)
        else:
            raw = self._openai_compatible(system, prompt, schema)
        return parse_json(raw)

    def test(self) -> str:
        return self.text("Bạn là trợ lý kiểm tra kết nối.", "Trả lời đúng một từ: OK", effort="low").strip()

    def list_models(self) -> list[str]:
        """Danh sách model key này dùng được (gateway LiteLLM trả đúng các model được cấp)."""
        try:
            if self.provider == "claude":
                import anthropic

                return sorted(m.id for m in anthropic.Anthropic(api_key=self.api_key).models.list())
            import openai

            return sorted(m.id for m in openai.OpenAI(api_key=self.api_key, base_url=self.base_url or None).models.list())
        except Exception as e:  # noqa: BLE001 — lỗi mạng/key của cả 2 SDK đều báo chung về UI
            raise AIError(t("Không lấy được danh sách model từ {label}: {error}", label=self.label, error=e)) from e

    # ---- Claude -------------------------------------------------------------
    def _claude(self, system: str, prompt: str, schema: dict | None, effort: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        output_config: dict = {"effort": effort}
        if schema:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        kwargs = dict(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config=output_config,
        )
        try:
            try:
                # fallbacks="default": nếu bị safety classifier từ chối, server tự chạy lại trên model dự phòng.
                resp = client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
                )
            except anthropic.BadRequestError:
                # Model được chọn không hỗ trợ fallbacks -> gọi lại bản thường.
                resp = client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise AIError(t("API key Claude không hợp lệ.")) from e
        except anthropic.PermissionDeniedError as e:
            raise AIError(t("API key Claude không có quyền dùng model này.")) from e
        except anthropic.NotFoundError as e:
            raise AIError(t("Model Claude không tồn tại: {model}", model=self.model)) from e
        except anthropic.RateLimitError as e:
            raise AIError(t("Claude đang giới hạn tốc độ (rate limit). Thử lại sau ít phút.")) from e
        except anthropic.APIConnectionError as e:
            raise AIError(t("Không kết nối được tới Claude API (kiểm tra mạng/proxy).")) from e
        except anthropic.APIStatusError as e:
            raise AIError(t("Claude API lỗi {code}: {message}", code=e.status_code, message=e.message)) from e

        if resp.stop_reason == "refusal":
            raise AIError(t("Claude từ chối yêu cầu này."))
        if resp.stop_reason == "max_tokens":
            raise AIError(t("Kết quả bị cắt do vượt max_tokens — thử chia nhỏ dữ liệu."))
        return "".join(b.text for b in resp.content if b.type == "text")

    # ---- OpenAI / Gemini / Gateway ------------------------------------------
    def _openai_compatible(self, system: str, prompt: str, schema: dict | None) -> str:
        import openai

        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        try:
            if schema:
                try:
                    resp = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {"name": "result", "schema": schema, "strict": True},
                        },
                    )
                except openai.BadRequestError:
                    # Gateway/model không hỗ trợ json_schema -> yêu cầu JSON qua prompt.
                    messages[0]["content"] += (
                        "\n\nChỉ trả về một JSON hợp lệ, không kèm giải thích, theo schema:\n"
                        + json.dumps(schema, ensure_ascii=False)
                    )
                    resp = client.chat.completions.create(model=self.model, messages=messages)
            else:
                resp = client.chat.completions.create(model=self.model, messages=messages)
        except openai.AuthenticationError as e:
            raise AIError(t("API key {label} không hợp lệ.", label=self.label)) from e
        except openai.NotFoundError as e:
            raise AIError(t("Model không tồn tại trên {label}: {model}", label=self.label, model=self.model)) from e
        except openai.RateLimitError as e:
            raise AIError(t("{label} đang giới hạn tốc độ hoặc hết quota.", label=self.label)) from e
        except openai.APIConnectionError as e:
            raise AIError(t("Không kết nối được tới {label} (kiểm tra mạng/base URL).", label=self.label)) from e
        except openai.APIStatusError as e:
            raise AIError(t("{label} lỗi {code}: {message}", label=self.label, code=e.status_code, message=e.message)) from e
        return resp.choices[0].message.content or ""


def parse_json(raw: str):
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(.+?)```", raw, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"(\{.*\}|\[.*\])", raw, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    raise AIError(t("AI trả về dữ liệu không phải JSON hợp lệ."))

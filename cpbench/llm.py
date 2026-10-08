"""Chat client for any OpenAI-compatible endpoint, plus a deterministic mock.

The benchmark talks to the model through ``POST {base_url}/chat/completions``
with ``tools`` in OpenAI function-calling format. That covers vLLM, Ollama
(``/v1``), llama.cpp server, Groq, Together, OpenRouter, Fireworks and the
OpenAI API itself, so the organizer can switch the fixed model with two
environment variables and the same student prompts can later be re-run on
other models.

Configuration (environment variables, see ``.env.example``):

    LLM_BASE_URL   e.g. http://localhost:11434/v1 or https://api.groq.com/openai/v1
    LLM_API_KEY    bearer token (Ollama accepts anything)
    LLM_MODEL      model id as the endpoint names it
    LLM_PROVIDER   "openai_compatible" (default) or "mock"
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional

import requests


class LLMError(RuntimeError):
    pass


class ChatResult:
    def __init__(self, content: Optional[str], tool_calls: List[Dict[str, Any]],
                 raw: Optional[Dict[str, Any]] = None, latency_s: float = 0.0,
                 usage: Optional[Dict[str, Any]] = None):
        self.content = content or ""
        self.tool_calls = tool_calls  # [{id, name, arguments(dict)}]
        self.raw = raw
        self.latency_s = latency_s
        self.usage = usage or {}

    def assistant_message(self) -> Dict[str, Any]:
        msg: Dict[str, Any] = {"role": "assistant", "content": self.content or None}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)}}
                for tc in self.tool_calls
            ]
        return msg


class LLMConfig:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 model: Optional[str] = None, provider: Optional[str] = None,
                 temperature: float = 0.0, timeout_s: Optional[float] = None, max_tokens: Optional[int] = None,
                 seed: Optional[int] = 7, extra_body: Optional[Dict[str, Any]] = None, env_prefix: str = "LLM"):
        env = lambda key, default=None: os.environ.get(f"{env_prefix}_{key}", default)  # noqa: E731
        self.base_url = (base_url or env("BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        self.api_key = api_key or env("API_KEY", "none")
        self.model = model or env("MODEL", "qwen2.5:7b-instruct")
        self.provider = (provider or env("PROVIDER", "openai_compatible")).lower()
        if self.provider == "mock":
            self.model = "mock"
        self.temperature = temperature
        self.timeout_s = float(timeout_s if timeout_s is not None else env("TIMEOUT_S", "90"))
        # Reasoning models (gpt-oss, Qwen3 in thinking mode) spend tokens before
        # answering, so the ceiling must be well above the length of a spoken reply.
        self.max_tokens = int(max_tokens if max_tokens is not None else env("MAX_TOKENS", "1200"))
        self.seed = seed
        # Provider-specific knobs as JSON, e.g. {"reasoning_effort": "low"} for
        # gpt-oss on Groq, or {"chat_template_kwargs": {"enable_thinking": false}}
        # for Qwen3 on vLLM.
        extra = extra_body if extra_body is not None else json.loads(env("EXTRA_BODY", "{}") or "{}")
        self.extra_body = dict(extra)

    def describe(self) -> Dict[str, Any]:
        return {"provider": self.provider, "model": self.model,
                "base_url": self.base_url if self.provider != "mock" else None,
                "temperature": self.temperature}


def _parse_tool_calls(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, tc in enumerate(message.get("tool_calls") or []):
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments")
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args) if raw_args.strip() else {}
            except json.JSONDecodeError:
                args = {"_unparsable": raw_args}
        elif isinstance(raw_args, dict):
            args = raw_args
        else:
            args = {}
        out.append({"id": tc.get("id") or f"call_{i}", "name": fn.get("name") or "", "arguments": args})
    return out


def chat(cfg: LLMConfig, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]],
         retries: int = 2) -> ChatResult:
    if cfg.provider == "mock":
        return MockModel().chat(messages, tools)

    url = f"{cfg.base_url}/chat/completions"
    body: Dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if cfg.seed is not None:
        body["seed"] = cfg.seed
    body.update(cfg.extra_body)
    headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"}

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=cfg.timeout_s)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            if resp.status_code >= 400:
                # Some servers reject "seed"; retry once without it.
                if "seed" in body and attempt == 0:
                    body.pop("seed", None)
                    continue
                raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            return ChatResult(message.get("content"), _parse_tool_calls(message), raw=data,
                              latency_s=time.time() - t0, usage=data.get("usage") or {})
        except (requests.RequestException, LLMError, ValueError) as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise LLMError(f"model call failed after {retries + 1} attempts: {last_err}")


# --------------------------------------------------------------------------
# Mock model: keyword rules so the kit and the service run with no model.
# It is intentionally mediocre (it ignores most of the system prompt) and is
# NOT the model used for grading. It exists so students can see the pipeline
# end to end and so the organizer can test the service offline.
# --------------------------------------------------------------------------

def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


class MockModel:
    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]]) -> ChatResult:
        # If the last message is a tool result, close the turn with a confirmation.
        last = messages[-1]
        if last.get("role") == "tool":
            try:
                payload = json.loads(last.get("content") or "{}")
            except json.JSONDecodeError:
                payload = {}
            if payload.get("status") == "FAILURE":
                return ChatResult("Uy, eso no me lo dejó hacer el carro. ¿Probamos otra cosa?", [])
            return ChatResult("Listo, ya quedó.", [])

        user_msgs = [m for m in messages if m.get("role") == "user"]
        text = _norm(user_msgs[-1].get("content", "")) if user_msgs else ""
        previous = _norm(user_msgs[-2].get("content", "")) if len(user_msgs) > 1 else ""
        calls: List[Dict[str, Any]] = []

        # Second turn: a bare "sí" confirms what was asked; otherwise merge
        # the clarification with the original request.
        if previous:
            if re.match(r"^\s*(si|sí|dale|claro|listo|hagale|de una)\b", text) or "abrelo" in text or "abrelas" in text:
                if "baul" in previous:
                    return ChatResult("", [{"id": "mock_0", "name": "open_close_trunk_door", "arguments": {"open_close": "OPEN"}}])
                if "altas" in previous:
                    return ChatResult("", [{"id": "mock_0", "name": "set_head_lights_high_beams", "arguments": {"on": True}}])
            text = previous + " " + text

        def call(tool_name: str, **args: Any) -> None:
            calls.append({"id": f"mock_{len(calls)}", "name": tool_name, "arguments": args})

        num = re.search(r"(\d+(?:[.,]\d+)?)", text)
        number = float(num.group(1).replace(",", ".")) if num else None

        if "limpiabrisas" in text or "limpia" in text and "brisas" in text:
            return ChatResult("Los limpiabrisas no los controlo yo. Puedo desempañar el parabrisas si quieres.", [])
        if "temperatura" in text or "grados" in text or "clima" in text or "aire" in text and number:
            if number is not None and 16 <= number <= 28:
                call("set_climate_temperature", zone="DRIVER", temperature=number)
            else:
                return ChatResult("¿A cuántos grados la quieres, entre 16 y 28?", [])
        elif "frio" in text and "copiloto" not in text:
            call("set_climate_temperature", zone="DRIVER", temperature=24)
        elif "empan" in text or "desempan" in text:
            call("set_fan_speed", level=3)
            call("set_fan_airflow_direction", direction="WINDSHIELD")
            call("set_air_conditioning", on=True)
            call("set_window_defrost", window="FRONT", on=True)
        elif "antiniebla" in text or "exploradoras" in text:
            call("set_head_lights_low_beams", on=True)
            call("set_fog_lights", on=True)
        elif "altas" in text:
            return ChatResult("¿Confirmas que prenda las luces altas?", [])
        elif "baul" in text:
            return ChatResult("¿Seguro que abro el baúl ahora?", [])
        elif "ventilador" in text and number is not None:
            call("set_fan_speed", level=int(number))
        elif "volumen" in text and number is not None:
            call("set_music_volume", level=int(number))
        elif "volumen" in text or ("musica" in text and ("baja" in text or "sube" in text)):
            call("set_music_volume", level=2 if "baja" in text else 6)
        elif "pausa" in text:
            call("pause_music")
        elif "musica" in text or "cancion" in text:
            call("play_music")
        elif "gasolinera" in text or "drogueria" in text or "farmacia" in text or "llevame" in text:
            dest = "droguería más cercana" if ("drogueria" in text or "farmacia" in text) else "gasolinera más cercana"
            call("set_navigation_destination", destination_name=dest)
        elif "ambiental" in text:
            color = "BLUE"
            for es, en in (("azul", "BLUE"), ("rojo", "RED"), ("verde", "GREEN"), ("morad", "PURPLE"),
                           ("amarill", "YELLOW"), ("blanc", "WHITE"), ("rosad", "PINK"), ("naranj", "ORANGE"),
                           ("apaga", "OFF")):
                if es in text:
                    color = en
            call("set_ambient_lights", color=color)
        elif "luz" in text and "lectura" in text:
            seat = "PASSENGER" if "copiloto" in text or "acompanante" in text else "DRIVER"
            call("set_reading_light", seat=seat, on="apaga" not in text)
        elif "luz" in text or "prende una" in text:
            return ChatResult("¿La luz de lectura o la ambiental?", [])
        elif "ventana" in text:
            if number is None and not previous and "copiloto" not in text and "sube" not in text and "cierra" not in text:
                return ChatResult("¿Cuál ventana y cuánto la abro?", [])
            window = "PASSENGER" if "copiloto" in text else "DRIVER"
            if "sube" in text or "cierra" in text:
                pct = 0
            elif number is not None:
                pct = int(number)
            elif "mitad" in text:
                pct = 50
            else:
                pct = 25
            call("open_close_window", window=window, percentage=pct)
        elif "silla" in text or "asiento" in text:
            call("set_seat_heating", seat="DRIVER", level=3)
        elif "maneja tu" in text or "autonomo" in text:
            call("set_autonomous_mode", on=True)
        elif "llama" in text:
            call("call_phone_by_contact", name="Mamá")
        else:
            return ChatResult("No te entendí bien, ¿me lo repites?", [])
        return ChatResult("", calls)

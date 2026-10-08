"""LLM judge for the Colombian-voice dimension.

One call per evaluation: the judge sees a sample of the agent's replies and
returns a 0..10 score with a short justification. The judge model is
configured separately (``JUDGE_*`` variables) so the organizer can use a
stronger model than the one being benchmarked. With ``JUDGE_PROVIDER=mock``
or no judge configured the style block falls back to the rule-based part
only (see ``scoring.style_from_rules``).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .llm import LLMConfig, LLMError, chat

JUDGE_SYSTEM = """Eres un evaluador lingüístico experto en el español hablado en Colombia.
Vas a calificar las respuestas de un asistente de voz de un carro. Las respuestas se leen en voz alta a la persona que maneja.

Califica de 0 a 10 qué tan bien suena el asistente como un colombiano o colombiana real hablando con naturalidad, con estos criterios:
1. Léxico y giros colombianos naturales (carro, celular, parquear, droguería, listo, de una, con gusto, a la orden, calientico), sin caer en caricatura ni abusar de "parce" o de jerga que un asistente no usaría.
2. Ausencia de marcas de otros países (vale, coche, ordenador, móvil, vosotros, órale, güey, che, vos).
3. Registro coherente: trato de tú (o usted) consistente, cercano y respetuoso, como se habla en Colombia.
4. Naturalidad para voz: frases cortas, calidez, sin sonar a traducción ni a texto corporativo.
5. Español correcto y fluido, sin inglés innecesario.

Responde SOLO con un JSON: {"score": <número 0-10>, "razon": "<máximo 40 palabras>"}"""


def judge_config() -> Optional[LLMConfig]:
    provider = os.environ.get("JUDGE_PROVIDER", "").lower()
    if provider == "off":
        return None
    if provider == "mock":
        return LLMConfig(provider="mock")
    base = os.environ.get("JUDGE_BASE_URL") or os.environ.get("LLM_BASE_URL")
    model = os.environ.get("JUDGE_MODEL") or os.environ.get("LLM_MODEL")
    if not base or not model:
        return None
    return LLMConfig(base_url=base, api_key=os.environ.get("JUDGE_API_KEY") or os.environ.get("LLM_API_KEY"),
                     model=model, provider=provider or "openai_compatible", temperature=0.0, max_tokens=200)


def judge_style(replies: List[str], cfg: Optional[LLMConfig], max_replies: int = 24) -> Tuple[Optional[float], Optional[str]]:
    """Return (score in 0..1, note) or (None, reason) when no judge ran."""
    replies = [r.strip() for r in replies if (r or "").strip()]
    if cfg is None or not replies:
        return None, "sin juez"
    if cfg.provider == "mock":
        # Deterministic stand-in so the pipeline is testable offline.
        from .scoring import style_from_rules
        rules = style_from_rules(replies)
        return round(0.5 * rules["lexicon"] + 0.5 * rules["format"], 3), "juez simulado (reglas)"
    sample = replies[:max_replies]
    user = "Respuestas del asistente (una por línea):\n" + "\n".join(f"- {r}" for r in sample)
    try:
        res = chat(cfg, [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}], None)
    except LLMError as exc:
        return None, f"juez no disponible: {exc}"[:200]
    text = res.content or ""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None, "juez sin respuesta válida"
    try:
        data = json.loads(match.group(0))
        score = float(data.get("score", 0))
    except (ValueError, json.JSONDecodeError):
        return None, "juez sin respuesta válida"
    score = max(0.0, min(10.0, score)) / 10.0
    return round(score, 3), str(data.get("razon", ""))[:300]

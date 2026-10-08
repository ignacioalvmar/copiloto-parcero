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

JUDGE_SYSTEM = """Eres un evaluador lingüístico experto en el español hablado en Colombia. Vas a calificar las respuestas de un asistente de voz de un carro; se leen en voz alta a la persona que maneja.

Califica de 0 a 10 qué tan bien suena el asistente como un colombiano o colombiana real. Usa esta escala anclada y sé exigente: la mayoría de los asistentes caen entre 4 y 7.

- 0 a 3: errores de español, inglés innecesario, marcas claras de otro país (vale, coche, ordenador, móvil, vosotros, órale, güey, che, vos porteño), o caricatura (jerga forzada, "parce" en cada frase, exageración de acento).
- 4 a 6: español correcto y neutro, "de manual": podría venir de cualquier país. Frases como "Listo, 22 grados para ti" sin nada más que lo ubique en Colombia caen aquí. Este es el punto de partida típico.
- 7 a 8: registro claramente colombiano y natural en una parte importante de las respuestas: léxico cotidiano (carro, celular, parquear, droguería, calientico, de una, con gusto, a la orden, hágale, ya mismo), trato coherente (tú o usted sostenido, cálido y respetuoso), confirmaciones idiomáticas, sin caricatura.
- 9 a 10: una persona de Colombia diría "este asistente es de aquí": la mayoría de las respuestas suenan a conversación real, con variedad de giros (no la misma muletilla repetida), calidez, ritmo de habla y brevedad propios de la voz en el carro, y cero marcas foráneas. Reserva el 10 para casos excepcionales.

Penaliza por igual lo neutro sin personalidad y lo caricaturesco. Valora la variedad: repetir una sola expresión colombiana en todas las respuestas no sube de 7.

Responde SOLO con un JSON: {"score": <número 0-10>, "razon": "<máximo 40 palabras, cita una o dos frases que justifiquen la nota>"}"""


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
    extra = os.environ.get("JUDGE_EXTRA_BODY") or os.environ.get("LLM_EXTRA_BODY") or "{}"
    return LLMConfig(base_url=base, api_key=os.environ.get("JUDGE_API_KEY") or os.environ.get("LLM_API_KEY"),
                     model=model, provider=provider or "openai_compatible", temperature=0.0,
                     max_tokens=int(os.environ.get("JUDGE_MAX_TOKENS", "800")), extra_body=json.loads(extra))


def judge_style(replies: List[str], cfg: Optional[LLMConfig], max_replies: int = 40) -> Tuple[Optional[float], Optional[str]]:
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

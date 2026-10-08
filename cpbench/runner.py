"""Runs one test case: system prompt + model + headless vehicle.

The loop mirrors WorlDrive's LLM seat: the model answers, every tool call
is executed against the vehicle model and its result is appended as a
``tool`` message, until the model answers without tool calls or the round
limit is reached. A case may have a second user turn (``followup``), used
for ambiguous and confirmation-gated cases.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any, Dict, List, Optional

from . import vehicle
from .llm import ChatResult, LLMConfig, LLMError, chat

FIXED_DATETIME = "jueves 15 de octubre de 2026, 18:30"
MAX_TOOL_ROUNDS_DEFAULT = 6  # one call per round on providers without parallel tool use


def render_system_prompt(template: str, state: Dict[str, Any], datetime_text: str = FIXED_DATETIME) -> str:
    return (template.replace("{{current_datetime}}", datetime_text)
                    .replace("{{vehicle_context}}", vehicle.vehicle_context_text(state)))


def run_case(case: Dict[str, Any], system_prompt: str, cfg: LLMConfig,
             max_tool_rounds: int = MAX_TOOL_ROUNDS_DEFAULT) -> Dict[str, Any]:
    """Execute a case and return a transcript the scorer can evaluate.

    Result keys: ``turns`` (one per user message, each with ``reply`` and
    ``calls``), ``calls`` (flat, ordered, with ``vehicle_state_after``),
    ``state_init``, ``state_final``, ``error`` (if the model failed).
    """
    state = vehicle.make_state(case.get("context_init"))
    state_init = copy.deepcopy(state)
    tools = vehicle.openai_tools()
    scope = case.get("tool_scope") or {}
    if scope.get("allow"):
        tools = [t for t in tools if t["function"]["name"] in set(scope["allow"])]
    if scope.get("deny"):
        tools = [t for t in tools if t["function"]["name"] not in set(scope["deny"])]

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": render_system_prompt(system_prompt, state)}
    ]
    user_turns = [case["message"]] + ([case["followup"]] if case.get("followup") else [])
    all_calls: List[Dict[str, Any]] = []
    turns: List[Dict[str, Any]] = []
    error: Optional[str] = None
    latency_total = 0.0
    tokens_total = 0
    t_start = time.time()

    for turn_index, user_text in enumerate(user_turns):
        messages.append({"role": "user", "content": user_text})
        turn_calls: List[Dict[str, Any]] = []
        reply = ""
        rounds = 0
        while True:
            try:
                result: ChatResult = chat(cfg, messages, tools)
            except LLMError as exc:
                error = str(exc)
                break
            latency_total += result.latency_s
            tokens_total += int((result.usage or {}).get("total_tokens") or 0)
            messages.append(result.assistant_message())
            if not result.tool_calls:
                reply = (result.content or "").strip()
                break
            rounds += 1
            for tc in result.tool_calls:
                res, ok = vehicle.execute(tc["name"], tc["arguments"], state)
                record = {
                    "turn": turn_index,
                    "round": rounds,
                    "call_id": tc["id"],
                    "name": tc["name"],
                    "args": tc["arguments"],
                    "ok": ok,
                    "result": res,
                    "vehicle_state_after": copy.deepcopy(state),
                }
                turn_calls.append(record)
                all_calls.append(record)
                # No "name" field here: some providers (Groq) reject messages[].name with HTTP 400.
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                 "content": json.dumps(res, ensure_ascii=False)})
            if rounds >= max_tool_rounds:
                # Give the model one last chance to speak without tools.
                try:
                    final = chat(cfg, messages, None)
                    latency_total += final.latency_s
                    reply = (final.content or "").strip()
                    messages.append(final.assistant_message())
                except LLMError as exc:
                    error = str(exc)
                break
            # Models sometimes return text alongside tool calls; keep the
            # last non-empty text as the reply if the loop ends on tools.
            if result.content and result.content.strip():
                reply = result.content.strip()
        turns.append({"user": user_text, "reply": reply, "calls": turn_calls, "tool_rounds": rounds})
        if error:
            break

    return {
        "case_id": case.get("id"),
        "category": case.get("category"),
        "turns": turns,
        "calls": all_calls,
        "state_init": state_init,
        "state_final": copy.deepcopy(state),
        "error": error,
        "latency_s": round(latency_total, 3),
        "wall_s": round(time.time() - t_start, 3),
        "tokens": tokens_total,
        "messages": messages,
    }

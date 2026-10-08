"""Load case sets, validate them and run a full evaluation."""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from . import vehicle
from .judge import judge_config, judge_style
from .llm import LLMConfig
from .runner import run_case
from .scoring import CATEGORIES, aggregate, score_case

PLACEHOLDERS = ("{{current_datetime}}", "{{vehicle_context}}")
MAX_PROMPT_CHARS = 12000


DEV_SET_PATH = os.path.join(vehicle.DATA_DIR, "dev_set.jsonl")
BASELINE_PROMPT_PATH = os.path.join(vehicle.DATA_DIR, "baseline_system_prompt.md")


def resolve_set(path: str) -> str:
    """Accept the shorthand ``dev`` for the packaged public set."""
    return DEV_SET_PATH if path in ("dev", "dev_set", "public") else path


def load_cases(path: str) -> List[Dict[str, Any]]:
    path = resolve_set(path)
    cases: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: JSON inválido: {exc}") from exc
    return cases


def validate_cases(cases: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    seen = set()
    for c in cases:
        cid = c.get("id", "?")
        if cid in seen:
            errors.append(f"{cid}: id duplicado")
        seen.add(cid)
        if c.get("category") not in CATEGORIES:
            errors.append(f"{cid}: categoría desconocida {c.get('category')}")
        if not isinstance(c.get("message"), str) or not c["message"].strip():
            errors.append(f"{cid}: falta message")
        for key in (c.get("context_init") or {}):
            if key not in vehicle.VEHICLE_FIELDS and key not in vehicle.EXTRA_DEFAULTS:
                errors.append(f"{cid}: campo de contexto desconocido {key}")
        expect = c.get("expect") or {}
        variants = expect.get("actions_any_of") or ([expect["actions"]] if expect.get("actions") else [])
        for actions in variants:
            for a in actions:
                if a.get("name") not in vehicle.TOOLS_BY_NAME:
                    errors.append(f"{cid}: herramienta desconocida {a.get('name')}")
        for rule in expect.get("forbidden") or []:
            name = rule.get("name") if isinstance(rule, dict) else rule
            if name not in vehicle.TOOLS_BY_NAME:
                errors.append(f"{cid}: herramienta prohibida desconocida {name}")
        for key in (expect.get("expected_state") or {}):
            if key not in vehicle.VEHICLE_FIELDS and key not in vehicle.EXTRA_DEFAULTS:
                errors.append(f"{cid}: expected_state con campo desconocido {key}")
        if (expect.get("must_ask") or expect.get("must_confirm")) and variants and not c.get("followup"):
            errors.append(f"{cid}: must_ask/must_confirm con acciones esperadas requiere followup")
    return errors


def check_prompt(prompt: str) -> Dict[str, Any]:
    warnings: List[str] = []
    errors: List[str] = []
    if not prompt or not prompt.strip():
        errors.append("el system prompt está vacío")
    if len(prompt) > MAX_PROMPT_CHARS:
        errors.append(f"el system prompt supera el máximo de {MAX_PROMPT_CHARS} caracteres ({len(prompt)})")
    for ph in PLACEHOLDERS:
        if ph not in prompt:
            warnings.append(f"no contiene el marcador {ph}; el agente no verá esa información")
    if re.search(r"(sk-[A-Za-z0-9]{10,}|api[_-]?key\s*[:=])", prompt, re.I):
        errors.append("parece contener una clave de API; quítala")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "chars": len(prompt)}


def strip_markdown_fence(prompt: str) -> str:
    """Students may keep the prompt inside a ``` fence in system_prompt.md."""
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", prompt, re.S)
    return m.group(1).strip() if m else prompt.strip()


def run_set(cases: List[Dict[str, Any]], system_prompt: str, cfg: LLMConfig,
            concurrency: int = 4, runs: int = 1, with_judge: bool = True,
            judge_cfg: Optional[LLMConfig] = None, max_tool_rounds: int = 4,
            include_transcripts: bool = False) -> Dict[str, Any]:
    """Run every case ``runs`` times (Pass^k: a case passes only if every run
    passes) and return the aggregate plus per-case details."""
    jobs = [(c, r) for c in cases for r in range(runs)]

    def work(job):
        case, _ = job
        run = run_case(case, system_prompt, cfg, max_tool_rounds=max_tool_rounds)
        return case, run, score_case(case, run)

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        results = list(pool.map(work, jobs))

    # Collapse repeated runs per case.
    per_case: Dict[str, Dict[str, Any]] = {}
    transcripts: Dict[str, List[Any]] = {}
    for case, run, sc in results:
        cid = case["id"]
        if cid not in per_case:
            per_case[cid] = dict(sc)
            per_case[cid]["runs"] = 0
            per_case[cid]["runs_passed"] = 0
            transcripts[cid] = []
        entry = per_case[cid]
        entry["runs"] += 1
        entry["runs_passed"] += 1 if sc["pass"] else 0
        if not sc["pass"] and entry["pass"]:
            # keep the failing explanation when any run failed
            entry.update({k: v for k, v in sc.items() if k not in ("runs", "runs_passed")})
        entry["pass"] = entry["runs_passed"] == entry["runs"]
        if include_transcripts:
            transcripts[cid].append(run.get("messages"))
    case_scores = [per_case[c["id"]] for c in cases]

    judge_score, judge_note = (None, "juez desactivado")
    if with_judge:
        jc = judge_cfg if judge_cfg is not None else judge_config()
        replies = [r for cs in case_scores for r in cs.get("replies") or []]
        judge_score, judge_note = judge_style(replies, jc)

    summary = aggregate(case_scores, judge_score, judge_note)
    summary["model"] = cfg.describe()
    summary["runs_per_case"] = runs
    out = {"summary": summary, "cases": case_scores}
    if include_transcripts:
        out["transcripts"] = transcripts
    return out


def format_report(result: Dict[str, Any], show_cases: bool = True) -> str:
    s = result["summary"]
    lines = []
    lines.append(f"PUNTAJE TOTAL: {s['total']:.1f} / 100   (modelo: {s['model']['model']}, corridas por caso: {s.get('runs_per_case', 1)})")
    t = s["tasks"]
    lines.append(f"  Tareas: {t['passed']}/{t['n']} superadas  ->  {100 * t['score']:.1f}")
    for cat in CATEGORIES:
        r = t["by_category"].get(cat)
        n = t["n_by_category"].get(cat, 0)
        if n:
            lines.append(f"    {cat:12s} {100 * (r or 0):6.1f} %  ({n} casos)")
    st = s["style"]
    judge = "sin juez" if st["judge"] is None else f"{100 * st['judge']:.0f}"
    lines.append(f"  Voz colombiana: {100 * st['score']:.1f}  (juez {judge}, léxico {100 * st['lexicon']:.0f}, formato {100 * st['format']:.0f})")
    if st.get("judge_notes"):
        lines.append(f"    juez: {st['judge_notes']}")
    if st.get("lexicon_penalties"):
        lines.append(f"    palabras que restan: {', '.join(st['lexicon_penalties'])}")
    if st.get("format_issues"):
        lines.append(f"    problemas de formato: {'; '.join(st['format_issues'])}")
    lines.append(f"  Latencia media por caso: {s['latency_mean_s']} s; tokens: {s['tokens_total']}")
    if show_cases:
        lines.append("")
        for cs in result["cases"]:
            mark = "OK " if cs["pass"] else "FALLÓ"
            lines.append(f"[{mark}] {cs['id']} ({cs['category']})")
            for reply in cs.get("replies") or []:
                lines.append(f"      dijo: {reply!r}")
            if cs.get("calls"):
                lines.append("      llamó: " + "; ".join(f"{c['name']}{json.dumps(c['args'], ensure_ascii=False)}" for c in cs["calls"]))
            for why in cs.get("why") or []:
                lines.append(f"      -> {why}")
    return "\n".join(lines)

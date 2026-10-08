"""Command line: ``python -m cpbench <command>``.

    python -m cpbench validate eval/mis_casos.jsonl
    python -m cpbench check system_prompt.md
    python -m cpbench run --set dev --prompt system_prompt.md [--mock]
    python -m cpbench chat --prompt system_prompt.md        # talk to the agent in the terminal
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import vehicle
from .bench import check_prompt, format_report, load_cases, run_set, strip_markdown_fence, validate_cases
from .llm import LLMConfig
from .runner import run_case


def _load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _read_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return strip_markdown_fence(fh.read())


def main(argv=None) -> int:
    _load_env()
    parser = argparse.ArgumentParser(prog="cpbench")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="validar un archivo de casos")
    p_val.add_argument("path")

    p_chk = sub.add_parser("check", help="revisar un system prompt (marcadores, tamaño)")
    p_chk.add_argument("path")

    p_run = sub.add_parser("run", help="correr un set de casos con un modelo")
    p_run.add_argument("--set", required=True)
    p_run.add_argument("--prompt", required=True)
    p_run.add_argument("--mock", action="store_true", help="usar el modelo simulado (sin red)")
    p_run.add_argument("--model")
    p_run.add_argument("--base-url")
    p_run.add_argument("--api-key")
    p_run.add_argument("--runs", type=int, default=1)
    p_run.add_argument("--concurrency", type=int, default=4)
    p_run.add_argument("--no-judge", action="store_true")
    p_run.add_argument("--json", help="guardar el resultado completo en este archivo")
    p_run.add_argument("--only", help="ids de casos separados por coma")

    p_chat = sub.add_parser("chat", help="conversar con el agente en la terminal")
    p_chat.add_argument("--prompt", required=True)
    p_chat.add_argument("--mock", action="store_true")
    p_chat.add_argument("--model")
    p_chat.add_argument("--base-url")
    p_chat.add_argument("--api-key")
    p_chat.add_argument("--context", help="JSON con el estado inicial del carro")

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        cases = load_cases(args.path)
        errors = validate_cases(cases)
        for e in errors:
            print("ERROR:", e)
        print(f"{len(cases)} casos, {len(errors)} errores")
        return 1 if errors else 0

    if args.cmd == "check":
        res = check_prompt(_read_prompt(args.path))
        for e in res["errors"]:
            print("ERROR:", e)
        for w in res["warnings"]:
            print("AVISO:", w)
        print(f"{res['chars']} caracteres; {'OK' if res['ok'] else 'con errores'}")
        return 0 if res["ok"] else 1

    def make_cfg(a) -> LLMConfig:
        if a.mock:
            return LLMConfig(provider="mock")
        return LLMConfig(base_url=a.base_url, api_key=a.api_key, model=a.model)

    if args.cmd == "run":
        cases = load_cases(args.set)
        errors = validate_cases(cases)
        if errors:
            for e in errors:
                print("ERROR:", e)
            return 1
        if args.only:
            wanted = set(args.only.split(","))
            cases = [c for c in cases if c["id"] in wanted]
        prompt = _read_prompt(args.prompt)
        chk = check_prompt(prompt)
        for w in chk["warnings"]:
            print("AVISO:", w)
        if not chk["ok"]:
            for e in chk["errors"]:
                print("ERROR:", e)
            return 1
        cfg = make_cfg(args)
        judge_cfg = LLMConfig(provider="mock") if args.mock else None
        result = run_set(cases, prompt, cfg, concurrency=args.concurrency, runs=args.runs,
                         with_judge=not args.no_judge, judge_cfg=judge_cfg)
        print(format_report(result))
        if args.json:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=1)
            print(f"\nResultado completo guardado en {args.json}")
        return 0

    if args.cmd == "chat":
        prompt = _read_prompt(args.prompt)
        cfg = make_cfg(args)
        context = json.loads(args.context) if args.context else {}
        print("Escribe lo que le dirías al carro. Vacío para salir. Cada mensaje es una conversación nueva;")
        print("escribe '+ texto' para continuar la conversación anterior con un segundo turno.\n")
        last_case = None
        while True:
            try:
                text = input("tú> ").strip()
            except EOFError:
                break
            if not text:
                break
            if text.startswith("+") and last_case is not None:
                last_case["followup"] = text[1:].strip()
                case = last_case
            else:
                case = {"id": "chat", "category": "single_step", "message": text, "context_init": context}
                last_case = case
            run = run_case(case, prompt, cfg)
            for turn in run["turns"]:
                for c in turn["calls"]:
                    status = "ok" if c["ok"] else "FALLÓ"
                    print(f"   [{status}] {c['name']} {json.dumps(c['args'], ensure_ascii=False)}")
                print(f"carro> {turn['reply']}")
            if run.get("error"):
                print("error:", run["error"])
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

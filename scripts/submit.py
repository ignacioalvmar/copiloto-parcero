#!/usr/bin/env python3
"""Envía tu system prompt al servidor de evaluación. Solo usa la librería estándar.

    python scripts/submit.py --team los-parceros --code XXXX              # set oculto (cuenta para la tabla)
    python scripts/submit.py --team los-parceros --code XXXX --dev        # set público, con detalle por caso
    python scripts/submit.py ... --prompt otro_prompt.md --server https://...

El servidor y el código de acceso los da la persona facilitadora. También puedes
guardarlos en variables de entorno: CP_SERVER, CP_TEAM, CP_CODE.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DEFAULT_SERVER = os.environ.get("CP_SERVER", "http://localhost:8080")


def read_prompt(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    return m.group(1).strip() if m else text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default=os.environ.get("CP_TEAM"), required=not os.environ.get("CP_TEAM"))
    ap.add_argument("--code", default=os.environ.get("CP_CODE"), required=not os.environ.get("CP_CODE"))
    ap.add_argument("--prompt", default="system_prompt.md")
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--dev", action="store_true", help="probar con el set público en vez de enviar al oculto")
    ap.add_argument("--json", help="guardar la respuesta completa en este archivo")
    args = ap.parse_args()

    body = json.dumps({"team": args.team, "access_code": args.code, "system_prompt": read_prompt(args.prompt)}).encode("utf-8")
    base = args.server.rstrip("/")
    url = base + ("/api/score" if args.dev else "/api/submit")
    print(("Probando con el set público" if args.dev else "Enviando al set oculto") + f" en {url} ...")
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            job = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("detail")
        except Exception:
            detail = exc.reason
        print(f"Rechazado ({exc.code}): {detail}")
        return 1
    except urllib.error.URLError as exc:
        print(f"No se pudo conectar al servidor: {exc.reason}")
        return 1
    for w in job.get("prompt_warnings") or []:
        print(f"  AVISO: {w}")

    # The server evaluates in the background; poll until done (30 s to a few minutes).
    t0 = time.time()
    data = None
    while True:
        time.sleep(3)
        try:
            with urllib.request.urlopen(base + "/api/jobs/" + job["job_id"], timeout=60) as resp:
                st = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            print(f"  (sin conexión, reintentando: {exc.reason})")
            continue
        elapsed = int(time.time() - t0)
        if st["status"] == "queued":
            print(f"  en cola, posición {st.get('queue_position', 0) + 1} ({elapsed} s)", end="\r", flush=True)
        elif st["status"] == "running":
            print(f"  evaluando con el modelo... ({elapsed} s)          ", end="\r", flush=True)
        elif st["status"] == "error":
            print(f"\nError: {st.get('error')}")
            return 1
        else:
            data = st["result"]
            print(" " * 60, end="\r")
            break

    s = data["summary"]
    print(f"\nPUNTAJE TOTAL: {s['total']:.1f} / 100   (modelo {s['model']})")
    print(f"  Tareas: {s['tasks']['passed']}/{s['tasks']['n']} superadas -> {s['tasks']['score']:.1f}")
    for key, cat in s["tasks"]["by_category"].items():
        rate = "–" if cat["pass_rate"] is None else f"{cat['pass_rate']:.1f} %"
        print(f"    {cat['label']:26s} {rate:>8s}  ({cat['n']} casos)")
    st = s["style"]
    judge = "n/a" if st["judge"] is None else f"{st['judge']:.0f}"
    print(f"  Voz colombiana: {st['score']:.1f}  (juez {judge}, léxico {st['lexicon']:.0f}, formato {st['format']:.0f})")
    if st.get("judge_notes"):
        print(f"    juez: {st['judge_notes']}")
    if st.get("lexicon_penalties"):
        print(f"    palabras que restan: {', '.join(st['lexicon_penalties'])}")
    if args.dev:
        print(f"  Pruebas públicas restantes esta hora: {data['remaining_this_hour']}\n")
        for c in data["cases"]:
            print(f"[{'OK ' if c['pass'] else 'FALLÓ'}] {c['id']} ({c['category']})")
            for r in c["replies"]:
                print(f"      dijo: {r!r}")
            if c["calls"]:
                print("      llamó: " + "; ".join(f"{k['name']}{json.dumps(k['args'], ensure_ascii=False)}" for k in c["calls"]))
            for why in c["why"]:
                print(f"      -> {why}")
    else:
        print(f"  Posición en tu cohorte: {data.get('rank_in_cohort')}   envíos restantes hoy: {data['remaining_today']}")
        for h in data.get("hints") or []:
            print(f"  pista: {h}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        print(f"\nRespuesta completa guardada en {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

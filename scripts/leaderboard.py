#!/usr/bin/env python3
"""Muestra la tabla de posiciones.  python scripts/leaderboard.py [--cohort COH1] [--server URL]"""
import argparse
import json
import os
import urllib.parse
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--server", default=os.environ.get("CP_SERVER", "http://localhost:8080"))
ap.add_argument("--cohort")
args = ap.parse_args()
url = args.server.rstrip("/") + "/api/leaderboard" + (f"?cohort={urllib.parse.quote(args.cohort)}" if args.cohort else "")
with urllib.request.urlopen(url, timeout=60) as resp:
    data = json.loads(resp.read().decode("utf-8"))
print(f"{'#':>3} {'Equipo':24s} {'Cohorte':8s} {'Total':>6s} {'Tareas':>7s} {'Voz':>6s} {'Envíos':>6s}")
for r in data["rows"]:
    print(f"{r['rank']:>3} {r['team']:24s} {r['cohort']:8s} {r['total']:>6.1f} {100*r['tasks']:>7.1f} {100*r['style']:>6.1f} {r['n_submissions']:>6d}")
if not data["rows"]:
    print("(todavía no hay envíos)")

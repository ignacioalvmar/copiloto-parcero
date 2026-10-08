# Tus propios casos

Pon aquí tus archivos `.jsonl` con casos nuevos (formato en `docs/CASOS.md`) y córrelos con:

    python -m cpbench run --set eval/mis_casos.jsonl --prompt system_prompt.md

El set público oficial está en `cpbench/data/dev_set.jsonl` (atajo: `--set dev`).

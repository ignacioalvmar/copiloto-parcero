# Casos propios y enfoque de datos

En [`casos_colombianos.jsonl`](casos_colombianos.jsonl) reuní 20 casos exploratorios que escribí para probar paráfrasis y situaciones en español colombiano. Los usé para **evaluar** el prompt, no para entrenar un modelo.

Consideré conjuntos de Hugging Face como `ylacombe/google-colombian-spanish`, `bookbot/slr72_dataset` y Common Voice en español filtrado por Colombia como posibles referencias para estudiar vocabulario y pronunciación. No los usé para entrenar ni ajustar el sistema, y no atribuyo a esos corpus las expresiones del prompt. El reto fija el modelo y califica respuestas escritas y llamadas a herramientas; no evalúa reconocimiento ni generación de voz.

Para repetir mi exploración desde la raíz del repositorio, con `cpbench` y un modelo local configurados, ejecuto:

```bash
python3 -m cpbench run --set eval/casos_colombianos.jsonl --prompt system_prompt.md
```

En la corrida exploratoria v7, Qwen2.5-16k pasó 4 de 20 casos. Ese resultado no es comparable con los puntajes oficiales ni corresponde a una evaluación local de v12. En el [resumen de resultados](RESULTADOS.md) documento las diferencias entre versiones y modelos.

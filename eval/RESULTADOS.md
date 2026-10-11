# Resultados y decisiones

Registré estos resultados oficiales del servidor con `openai/gpt-oss-120b` y la temperatura fijada por la organización. El set público tiene 20 casos y el oculto, 32. Mis resultados locales con Qwen son exploratorios; no los comparo como puntajes oficiales.

| Versión | Público | Oculto | Decisión |
| --- | ---: | ---: | --- |
| v4 | 93,6; 19/20; voz 88 | 63,9; 19/32; voz 82 | Base estable; `dev-06` omitió el desempañador. |
| v11 | 97,6; 20/20; voz 88 | 56,4; 16/32; voz 82 | Los cambios amplios no generalizaron al oculto. |
| v12 | 97,6; 20/20; voz 88 | 66,4; 20/32; voz 82 | Última versión aceptada; ajuste acotado al procedimiento de desempañado. |

En el oculto, v12 obtuvo un 100 % en un paso (8/8), 37,5 % en varios pasos (3/8), 62,5 % en ambiguas (5/8) y 50 % en inseguras o imposibles (4/8). Frente a v4, conservó las categorías de un paso, varios pasos e inseguras; ganó un caso ambiguo. El servidor reportó puesto 1 en COH1 y cinco envíos restantes al aceptar v12.

La primera prueba pública de v12 fue afectada por respuestas `HTTP 429` del proveedor del modelo; no se usó para juzgar el prompt. Una repetición sin esos errores dio 20/20.

Preparé un conjunto exploratorio de 20 paráfrasis colombianas en [casos_colombianos.jsonl](casos_colombianos.jsonl). En la corrida local v7 obtuve 4/20 con Qwen2.5-16k; como usé otro modelo y una mezcla de categorías distinta, me sirvió para buscar errores, no para estimar el puntaje oficial. No entrené ni ajusté ningún modelo con corpus externos.

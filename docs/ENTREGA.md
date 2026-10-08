# Entrega final y evaluación

## Qué se entrega

Todo en tu repositorio, antes de la fecha y hora límite de tu cohorte (hora de Colombia). No hay prórrogas individuales: las cuatro cohortes se tratan igual.

1. **`system_prompt.md`** con el prompt final. Debe ser el mismo texto de tu último envío aceptado al set oculto; si difieren, vale el del servidor.
2. **Video en inglés, máximo 3 minutos.** Grabación de pantalla con voz. Muestra el asistente respondiendo (la terminal con `python -m cpbench chat`, el formulario web o la salida del set público sirven) y explica la decisión de diseño más importante de tu prompt: qué problema viste, qué cambiaste, qué pasó con el puntaje. Enlace (YouTube no listado, Drive o la plataforma del curso) en tu `README.md`.
3. **`REFLEXION.md`**, 300 a 500 palabras, español o inglés, con la plantilla de `templates/REFLEXION.md`.
4. **`AI_LOG.md`** con la plantilla de `templates/AI_LOG.md`: qué asistentes de IA usaste, tres prompts que te sirvieron, uno que te engañó y por qué.
5. **`README.md`** de tu repositorio con: nombre del equipo tal como aparece en la tabla, integrantes, enlace al video, puntaje final del set oculto, y una frase sobre qué funciona y qué no.

Opcional pero valorado: tus propios casos de prueba (`eval/mis_casos.jsonl`) y los resultados locales que te ayudaron a decidir.

## Pesos

| Componente | Peso | Cómo se mide |
| --- | --- | --- |
| Puntaje del set oculto | 40 % | último envío aceptado antes de la fecha límite, con el modelo fijo |
| Calidad del prompt | 25 % | rúbrica del jurado sobre el texto del prompt |
| Criterio y extensión | 15 % | rúbrica: casos propios, análisis de fallos, decisiones justificadas |
| Video | 10 % | rúbrica: muestra en vez de afirmar, explica una decisión, inglés comprensible, dentro de 3 minutos |
| Reflexión y registro de IA | 10 % | rúbrica: especificidad, honestidad, una lección transferible |

## Rúbrica del jurado (0 a 4 por fila)

- **Calidad del prompt.** 0: desordenado o contradictorio. 2: claro, con reglas y ejemplos razonables. 4: estructura limpia, ejemplos que cubren los cuatro tipos de petición, políticas convertidas en secuencias concretas, voz colombiana definida sin caricatura, sin relleno.
- **Criterio y extensión.** 0: solo cambios cosméticos. 2: iteró con la salida del set público y lo documenta. 4: escribió casos propios, encontró un modo de fallo no cubierto por el set público y lo resolvió, o analizó con datos por qué una idea no funcionó.
- **Video.** 0: no hay o no se entiende. 2: muestra el asistente. 4: muestra, explica una decisión con claridad, dura 3 minutos o menos, inglés comprensible.
- **Reflexión y registro.** 0: faltan. 2: genéricos. 4: incidentes concretos, honestidad sobre lo que la IA hizo mal, una lección que servirá en otro proyecto.

Dos personas del jurado por entrega; las diferencias de más de un punto por fila se discuten. El jurado ve el puntaje del servidor solo después de calificar la rúbrica.

## Reconocimiento

Por cohorte: ganador y segundo puesto, anunciados dentro de las 72 horas siguientes, con retroalimentación por categoría para todos los participantes. Al terminar la gira: el mejor prompt entre las cuatro cohortes, probado además en otros modelos. Los mejores equipos quedan invitados a una conversación sobre los programas de maestría y doctorado de THI.

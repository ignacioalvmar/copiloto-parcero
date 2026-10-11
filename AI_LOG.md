# Registro de uso de IA

**Asistentes usados y para qué**

- **Codex (OpenAI):** lectura del README y la rúbrica, análisis de salidas, borradores y revisiones del system prompt, organización de resultados, reflexión y guion.
- **Copilot:** una respuesta inicial sobre cómo usar conjuntos de datos dentro de las reglas del reto; se contrastó después con el README.
- **Qwen2.5-16k vía Ollama:** modelo local para exploraciones de casos; no fue el modelo oficial ni se usó para entrenar el sistema.
- **Modelo oficial del benchmark:** `openai/gpt-oss-120b`, fijado por la organización. No se ajustaron sus pesos.

**Tres prompts que me sirvieron**

1. “Lee en detalle el README y propone un plan que respete las reglas del reto.” Sirvió para confirmar que se calificaba el texto del prompt y las acciones con herramientas, no un modelo TTS/ASR ajustado.
2. “Analiza la salida caso por caso: separa llamadas faltantes, estado final, ambigüedad, seguridad y errores del modelo.” Ayudó a distinguir fallos del prompt de respuestas incompletas por `HTTP 429`.
3. “Compara v4 y la variante que modifica solo el desempañado; evita envíos oficiales sin autorización y no afirmes una mejora hasta ver el resultado.” Llevó a conservar v4 como base y medir v12 antes de enviarla.

**Uno que me engañó**

Pedí cambios para subir varias categorías débiles. La IA propuso un bloque amplio de reglas y dio demasiado peso al 20/20 público de v11 como señal de generalización. El resultado oculto de v11 fue 56,4, por debajo del 63,9 de v4. No se podía saber qué regla causó la caída porque se modificaron varias juntas. Lo detecté contrastando los resultados oficiales por categoría y regresé a v4 para probar un cambio más acotado en v12. La mejora posterior de v12 no demuestra que todos los cambios generales sean malos; muestra que debí aislarlos.

**Porcentaje aproximado del texto final del system prompt escrito por IA sin cambios:** 90 %. Es una estimación: la IA redactó gran parte del texto y los ejemplos; yo elegí la base, pedí cambios, revisé los resultados y decidí qué versión enviar.

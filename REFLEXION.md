# Reflexión

**Equipo:** ParceroA  
**Integrante:** Tannia Lucia Hernandez  
**Puntaje final en el set oculto:** 66,4/100 (20/32 tareas; voz 82/100)

## Qué quería lograr

Quería que el copiloto ejecutara las acciones en vez de prometerlas, aclarara ambigüedades relevantes y sonara colombiano sin exagerar los modismos. Consideré entrenarlo con corpus de voz y pronunciación, pero el README fija el modelo y evalúa texto y llamadas a herramientas. Por eso no hice fine-tuning. Escribí 20 paráfrasis colombianas para explorar situaciones adicionales (`eval/casos_colombianos.jsonl`).

## Qué cambié y qué pasó

La v4 obtuvo 93,6 en el set público (19/20) y 63,9 en el oculto (19/32). El fallo público que podía aislar era el desempañado: el asistente omitía una acción necesaria. Después probé v11, que agrupaba varios cambios generales. Aunque llegó a 20/20 en público, bajó a 56,4 en el oculto (16/32); como cambiaron varias reglas a la vez, no pude atribuir la caída a una sola.

Volví a v4 e hice v12 con un ajuste concentrado en desempañar: explicitar el estado final, completar las cuatro llamadas requeridas y verificar el clima antes de responder. V12 alcanzó 20/20 en público y 97,6 puntos. En el oculto obtuvo 66,4 (20/32), 2,5 puntos más que v4. Subió de 4/8 a 5/8 en ambiguas; varios pasos quedó en 3/8 e inseguras en 4/8. El servidor reportó el primer puesto de la cohorte. La voz quedó en 82, igual que v4.

## Dónde me ayudó la IA y dónde me engañó

Codex ayudó a leer las reglas, revisar llamadas y argumentos, y comparar los resultados por categoría. También me llevó a confiar demasiado en que un paquete de cambios que mejorara el set público se trasladaría al oculto: v11 mostró lo contrario. Lo detecté en el resultado oficial, no en una predicción local. Volver a la v4 y cambiar una zona concreta permitió evaluar mejor la hipótesis.

## Qué haría con un segundo día

Trabajaría primero los varios pasos y las negativas seguras, con paráfrasis propias equilibradas por categoría. Haría un cambio por versión y separaría resultados del modelo local de los del modelo oficial. Para la voz, pediría a hablantes colombianos que revisaran frases reales en vez de añadir más expresiones automáticamente.

## Qué aprendí

Un prompt puede sonar convincente y aun así fallar si no completa una llamada o deja mal el estado del carro. Un 20/20 público tampoco garantiza generalización. Los datos y el resultado oculto deben decidir qué cambio conservar, no la seguridad con que una IA prediga que va a funcionar.

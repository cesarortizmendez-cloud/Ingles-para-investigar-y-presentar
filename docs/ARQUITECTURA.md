# Arquitectura (incremento 1)

## Decisión: apps por dominio, capítulos como paquetes de contenido

Se eligió **una Django app por responsabilidad estable** (cuentas, catálogo curricular, actividades, audio, repaso,
evaluación, portafolio, tutor) y **cada capítulo como un paquete de contenido JSON versionado** en `content/`.
No se creó una app por capítulo.

Razones (ver §14 de la especificación):

- Los 24 capítulos comparten los mismos formatos de actividad, rúbricas, repaso y reglas de cierre. Con una app por
  capítulo, cada cambio del motor tendría que repetirse o delegarse 24 veces.
- Un capítulo es contenido, no comportamiento: objetivos, recursos, actividades y claves. Expresarlo como datos
  permite validarlo con un contrato (`learning_core/contract.py`), versionarlo y editarlo sin tocar código.
- Para trabajar con la IA con contexto acotado basta con enviar el archivo del capítulo y citar IDs
  (`C11.4.a2`), no el proyecto completo.

Si en el futuro un capítulo necesita comportamiento propio (p. ej. un simulador de congreso en C24), se agrega un
**tipo de actividad** nuevo en `learning_core/grading.py` y su plantilla en `templates/activities/`, reutilizable por
cualquier capítulo.

## Capas

```
templates/ + static/js/app.js     presentación; el navegador hace TTS, grabación y ASR opcional
        │
Django apps (views/services)      orquestan: leen el paquete vigente, guardan intentos, llaman a learning_core
        │
learning_core/ (Python puro)      decide: corrección, rúbricas, repaso, estado del capítulo, diagnóstico, contrato
        │
content/*.json                    datos editoriales versionados
```

`learning_core` no importa Django: se prueba con `pytest tests/` en milisegundos. Las sugerencias del tutor nunca
cambian el estado académico; ese estado solo lo calcula `learning_core.progression` a partir de intentos y rúbricas.

## Modelo conceptual

curso (`content/course.json`) → etapa → capítulo (`ContentPackage`) → lección → actividad.

| Modelo | App | Qué guarda |
|---|---|---|
| `ContentPackage` | curriculum | Una versión inmutable de un capítulo o diagnóstico (JSON completo, checksum, estado editorial, vigente) |
| `ChapterProgress` | curriculum | Estado del alumno en el capítulo, fecha de aprobación provisional, consolidación y recuperación |
| `Attempt` | activities | Respuesta, versión de contenido, ayudas, tiempo, resultado, retroalimentación, origen (lección, repaso, diferido, diagnóstico) |
| `Recording` | voice | Audio (BinaryField), transcripción editable, errores del ASR señalados, autorizaciones separadas |
| `ReviewItem` | review | Etapa e intervalo de repaso de una actividad o unidad léxica, historial |
| `RubricScore` | assessment | Puntuación 0–4 por criterio, total ponderado, tipo de evaluador (auto/humano) |
| `DiagnosticResult` | assessment | Estimación por habilidad, confianza y recomendación |
| `Profile` | accounts | Especialidad, disponibilidad, congresos, familiaridad con papers, voz, modo sin micrófono |

### IDs estables

- Capítulo `C11`, objetivo `C11-O1`, léxico `C11-LX01`, recurso `C11-R01`, lección `C11.1`, actividad `C11.1.a1`,
  diferido `C11.D.a1`, grupo de variantes `C11-final`.
- Los intentos guardan `activity_id` y la versión exacta del paquete, así que editar un capítulo no destruye ni
  reinterpreta intentos anteriores.

### Versionado de contenido

- `import_content` rechaza un paquete con el mismo número de versión y contenido distinto: hay que subir la versión.
- En `/admin/`, guardar cambios en el JSON crea una versión nueva (sube el parche) y la deja vigente.
- Estados editoriales: `borrador`, `revisado`, `publicado`. C01 y C11 están en `borrador` hasta su revisión.

## Reglas de evaluación implementadas (sin cambios respecto de la especificación)

- Cierre de capítulo: ≥ 80 % en ítems de comprobación (primer intento de cada uno) + tarea integradora ≥ 70/100 sin
  criterio esencial < 2/4 → aprobado provisionalmente; confirmación diferida ≥ 75 % desde el día 7 → consolidado.
  Si la diferida falla: recuperación específica, sin borrar historial.
- Rúbricas oral, interacción, lectura y escritura con los pesos de §12; total = Σ peso × puntuación/4.
- Repaso: 1, 3, 7, 14, 30 días; acierto con ayuda no avanza; tope diario 20 con redistribución.
- Diagnóstico: estimación por habilidad con confianza; muestra insuficiente → «se solicitará evidencia adicional».

Una decisión de interpretación: la tarea integradora se aprueba con la evaluación humana si existe y, si no, con la
autoevaluación. La especificación recomienda revisión humana periódica pero no la exige para el cierre; si se
quiere exigirla, basta con cambiar `curriculum.services.task_evaluation`.

## Audio y voz

- Modelos de audio: voz sintetizada del navegador (`speechSynthesis`), siempre etiquetada como «voz sintetizada».
  La velocidad se ajusta sin alterar el tono. Los paquetes admiten `audio.file` para audio humano cuando exista.
- Grabación: `MediaRecorder`, prueba de micrófono con medidor, detección de silencio, mensajes distintos para
  micrófono bloqueado, sin micrófono, en uso, silencio y servicio no disponible (AUD08).
- Transcripción: reconocimiento del navegador si existe (Chrome/Edge), siempre editable (AUD05). La
  retroalimentación oral se limita a la transcripción y lo declara; no se infieren fonemas ni entonación (AUD06).
- Sin micrófono: se puede estudiar; la habilidad oral queda «pendiente de evidencia», nunca aprobada.
- Almacenamiento en base de datos porque Vercel no tiene disco persistente. Para muchos usuarios conviene mover el
  audio a almacenamiento de objetos (Vercel Blob o S3): el cambio queda encapsulado en `voice/`.

## Seguridad y privacidad

- Solo el dueño escucha sus grabaciones; el personal solo si el alumno autorizó compartir.
- Exportación JSON de todo el progreso; eliminación de grabaciones o de la cuenta completa (en cascada).
- Redirecciones `next` restringidas al mismo sitio; CSRF en todas las acciones; cookies seguras en producción.

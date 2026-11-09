# Incremento 1 · Sección vertical utilizable

Fecha: 5 de noviembre de 2026.

## Qué incluye

Perfil, diagnóstico breve, catálogo de 24 capítulos (2 disponibles), C01 y C11 piloto completos (seis lecciones,
comprobación, tarea integradora con variantes de especialidad en C11, confirmación diferida), actividades objetivas
y abiertas, reproducción de modelos y grabación, repaso espaciado, rúbricas, portafolio, exportación, eliminación de
datos y edición versionada de contenidos.

## Funciones reales, simuladas y ausentes

| Función | Estado |
|---|---|
| Corrección de ítems cerrados (9 tipos) | **Real**, determinista |
| Rúbricas y regla de tarea | **Real**; la puntuación la asigna una persona (autoevaluación o evaluador) |
| Cierre de capítulo, confirmación diferida, recuperación | **Real** |
| Repaso espaciado de actividades y léxico | **Real** |
| Diagnóstico por habilidad con confianza | **Real** para ítems cerrados; escritura y habla dependen de autoevaluación (confianza baja) |
| Comentarios a respuestas abiertas | **Simulado**: reglas definidas en el contenido; se muestra siempre «no es IA ni evaluación final» |
| Preguntas de seguimiento orales | **Simulado**: guionizadas en el contenido (`tutor/providers.py`, «Tutor simulado») |
| Voz de los modelos | **Real**, pero sintetizada por el navegador y etiquetada; calidad según navegador |
| Transcripción de la voz del alumno | **Real si el navegador lo ofrece** (Chrome/Edge); editable |
| Evaluación de pronunciación | **No disponible**, y así se declara |
| Conversación con IA, lector de papers propios, simulador de congreso, analítica | No incluidos (P1) |
| Prueba de desafío para omitir contenidos, cápsulas de refuerzo | No incluidas; el diagnóstico las recomienda |

## Dependencias externas

- Python: Django 5.2, dj-database-url, psycopg 3, whitenoise.
- Producción: Postgres (Neon, Vercel Postgres o Supabase) y Vercel.
- Navegador: `speechSynthesis`, `MediaRecorder`, `getUserMedia`; `SpeechRecognition` opcional.
- Ningún servicio de IA ni de voz de pago.

## Verificación hecha en este incremento

- 29 pruebas de `learning_core` pasan (`pytest tests/`), incluidas las claves de la §17: 8 semanas, 120 y 138
  unidades/día, 4,0 % y 3,5 %, 15 % mayor, 0,5 puntos porcentuales; los cálculos de los casos de transferencia y
  diferido; pesos de rúbricas que suman 100; umbrales de cierre.
- Los tres paquetes de contenido cumplen el contrato editorial.
- Todos los archivos Python compilan; el JavaScript pasa `node --check`.
- **No se ejecutó Django** (no estaba instalado en el entorno de desarrollo). `curriculum/tests.py` contiene 16
  pruebas de integración del recorrido completo para ejecutar con `python manage.py test`.

## Criterios de aceptación (§13, P0)

| Función | Criterio | Estado |
|---|---|---|
| Perfil y diagnóstico | Recomienda inicio por habilidad y refuerzos sin asumir que todo es B1 | Cumplido en lógica y pruebas puras; verificar en navegador |
| Ruta y catálogo | Objetivos, prerrequisitos, estado y producto de cada capítulo | Cumplido (capítulos no implementados se muestran «en preparación», sin relleno) |
| Motor de actividades | Respuestas objetivas y abiertas, explicaciones y reintentos | Cumplido |
| Audio y grabadora | Escuchar, grabar, comparar; maneja permiso denegado | Cumplido en código; probar en Chrome, Edge, Firefox y Safari |
| Repaso espaciado | Recupera contenidos y errores en días distintos, con historial | Cumplido; el repaso reutiliza la misma actividad (aún no cambia contexto, ver pendientes) |
| Evaluación y portafolio | Conserva evidencias y muestra qué habilidad se demostró | Cumplido |
| Edición de contenidos | Cambiar una lección no modifica el motor ni destruye intentos | Cumplido (versionado + contrato) |
| Control del usuario | Revisar datos, exportar progreso, eliminar grabaciones | Cumplido |

## Pendientes y supuestos para revisar

1. Revisión editorial de C01 (redactado completo por Claude) y de los casos de transferencia de C11; luego cambiar
   `status` a `revisado`.
2. El repaso de actividades repite la misma actividad; la §5 pide cambiar contexto y forma. Próximo paso: variantes
   de repaso por actividad (`review_variants`).
3. Evaluación humana: hoy un usuario `is_staff` puede evaluar intentos de grabaciones compartidas abriendo
   `/evaluacion/intento/<id>/rubrica/`. Falta una bandeja de revisión y doble evaluador (P2).
4. Pruebe la grabación en los navegadores reales de sus alumnos; Safari graba en `audio/mp4`.
5. Considere almacenamiento de objetos para audio si el piloto supera unas decenas de usuarios.

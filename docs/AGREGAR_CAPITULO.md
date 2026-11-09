# Cómo agregar un capítulo sin alterar los anteriores

1. Copie `content/chapters/C11.json` como plantilla a `content/chapters/C05.json` (por ejemplo) y cambie `id`,
   `title`, `stage`, `order` y todos los IDs internos al prefijo nuevo (`C05-O1`, `C05.1.a1`…).
2. Complete el contrato editorial (§14). El validador exige:
   - 3 a 5 objetivos; 8 a 12 unidades léxicas prioritarias;
   - seis lecciones en el orden `comprender, descubrir, escuchar, recuperar, producir, tarea`;
   - ítems de comprobación (`"role": "check"`), una tarea integradora (`"role": "final"`) con rúbrica, y una
     confirmación diferida con ítems de corrección determinista;
   - autoría y licencia en cada recurso, y `fictional_data` declarado;
   - claves coherentes (respuesta entre las opciones, espacios `[[n]]` iguales a `gaps`, etc.).
3. Valide y cargue:

   ```bash
   python manage.py validate_content content/chapters/C05.json
   python manage.py import_content
   ```

4. El catálogo lo muestra automáticamente como disponible (el título y la etapa vienen de `content/course.json`).

No se toca código ni los paquetes de otros capítulos. Para corregir un capítulo existente, edite su JSON, **suba
`version`** (p. ej. 1.0.0 → 1.0.1), agregue una línea en `quality.changelog` y vuelva a importar. Los intentos
anteriores siguen asociados a la versión con que se hicieron.

## Tipos de actividad disponibles

| Tipo | Uso | Campos clave |
|---|---|---|
| `choice` | Selección con justificación o evidencia opcional | `options`, `answer`, `justify`, `evidence.sentences/answer` |
| `cloze` | Conectores, tiempos, grupos de palabras | `text` con `[[1]]`, `gaps.{n}.accept/near/hint` |
| `ordering` | Movimientos de un abstract, orden de oración | `items`, `answer`, `justify` |
| `numeric` | Cifras, porcentajes, puntos porcentuales | `fields[].answer/tolerance/hint` |
| `short_text` | Recuperar una expresión desde la intención | `accept`, `near`, `hint` |
| `listening` | Comprender antes de leer (transcripción después) | `audio.text/voice`, `transcript`, `questions` |
| `dictation` | Dictado breve de datos y expresiones | `audio.text`, `answer` |
| `open_text` | Escritura con comentarios por reglas | `min_words`, `max_words`, `checks`, `rubric` |
| `oral` | Grabación, shadowing, interacción | `min_seconds`, `max_seconds`, `model`, `follow_ups`, `checks`, `rubric`, `self_check` |

Variantes por especialidad: use el mismo `variant_group` y distinto `specialty` (`industrial`, `comercial`,
`informatica`); el alumno ve la de su perfil y puede ver las demás.

## Pedir cambios a la IA con contexto acotado

Envíe solo el archivo del capítulo y cite IDs: «En `C11.4.a5`, agrega un cuarto espacio con *however*». No envíe el
curso completo para corregir una lección.

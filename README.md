# Inglés para investigar y presentar

Aplicación Django para adultos chilenos hispanohablantes (base aproximada B1) que necesitan leer publicaciones
científicas y presentar investigación en ámbitos comercial, industrial e informático.

- Requisitos pedagógicos: [`docs/ESPECIFICACION.md`](docs/ESPECIFICACION.md) (v1.0, C. Ortiz)
- Arquitectura y decisiones: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)
- Cómo agregar un capítulo: [`docs/AGREGAR_CAPITULO.md`](docs/AGREGAR_CAPITULO.md)
- Estado del incremento 1 (qué es real, qué es simulado, criterios de aceptación): [`docs/INCREMENTO_01.md`](docs/INCREMENTO_01.md)

## Despliegue (GitHub → Vercel → Neon)

Guía paso a paso: [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md). En resumen: subir a GitHub, importar en Vercel, definir
`DJANGO_SECRET_KEY` y el administrador, conectar Neon desde *Storage*, y desplegar. Cada despliegue ejecuta
`vercel_build.py` → `python manage.py preparar_produccion` (migraciones + contenido + administrador).

## Puesta en marcha local

Requiere Python 3.12 (3.10+ funciona).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    ·    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Desarrollo local sin variables: DEBUG=1 usa SQLite y una clave de desarrollo
set DJANGO_DEBUG=1            # PowerShell: $env:DJANGO_DEBUG="1"   ·   bash: export DJANGO_DEBUG=1

python manage.py makemigrations accounts curriculum activities voice review assessment
python manage.py migrate
python manage.py validate_content      # revisa el contrato editorial de content/
python manage.py import_content        # carga C01, C11 y el diagnóstico DX01
python manage.py createsuperuser       # acceso a /admin/ (edición de contenidos)
python manage.py runserver
```

> Las migraciones no vienen generadas porque este incremento se escribió en un entorno sin Django instalado.
> Genérelas una vez con el comando de arriba y súbalas al repositorio junto con el resto.

## Pruebas

```bash
pytest tests/                 # lógica pedagógica pura (no necesita Django ni base de datos)
python manage.py test         # recorrido completo de la aplicación (Django)
```

## Despliegue en Vercel

1. Cree una base Postgres (Neon, Vercel Postgres o Supabase) y copie su `DATABASE_URL`.
2. En Vercel → *Settings → Environment Variables* defina `DJANGO_SECRET_KEY` (larga y aleatoria) y `DATABASE_URL`.
   No defina `DJANGO_DEBUG` en producción.
3. Importe el repositorio de GitHub en Vercel. Vercel detecta Django por `manage.py`, usa `WSGI_APPLICATION`
   (`config.wsgi.application`) y ejecuta `collectstatic` porque `STATIC_ROOT` está definido.
4. Vercel no ejecuta migraciones. Desde su computador, apuntando a la base de producción:

   ```bash
   set DATABASE_URL=postgres://...   # la misma de Vercel
   set DJANGO_SECRET_KEY=...
   python manage.py migrate
   python manage.py import_content
   python manage.py createsuperuser
   ```

   Repita `migrate` cuando cambien los modelos e `import_content` cuando cambie `content/`.

Limitaciones conocidas en Vercel: el disco es efímero (por eso las grabaciones se guardan en la base de datos) y el
cuerpo de cada solicitud no puede superar 4,5 MB (las grabaciones se limitan a 4 MB y 180 s).

## Estructura

```
config/          settings, urls, wsgi, utilidades HTTP
learning_core/   lógica pedagógica pura y probada: corrección, rúbricas, repaso, cierre, diagnóstico, contrato
content/         paquetes de contenido versionados (JSON): course.json, chapters/C01.json, chapters/C11.json, diagnostic/DX01.json
accounts/        usuario y perfil (especialidad, disponibilidad, congresos, voz de referencia, modo sin micrófono)
curriculum/      paquetes de contenido versionados, catálogo, capítulos, lecciones, confirmación diferida
activities/      motor de actividades (intentos, ayudas, tiempos) y plantillas de cada tipo
voice/           grabaciones, transcripción editable, autorizaciones
review/          repaso espaciado de actividades y léxico
assessment/      rúbricas, diagnóstico
portfolio/       evidencias, exportación y eliminación de datos
tutor/           punto de extensión para IA (en este incremento: simulado y declarado como tal)
templates/, static/
```

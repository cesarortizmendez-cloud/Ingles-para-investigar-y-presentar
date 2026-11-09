# Despliegue: GitHub → Vercel → Neon

Guía paso a paso (Windows, Command Prompt de VS Code). La app queda en `https://<tu-proyecto>.vercel.app`.

## Qué hace el proyecto solo

- **Vercel detecta Django** por `manage.py` y usa `config/wsgi.py` (declarado también en `pyproject.toml`).
- **Archivos estáticos**: Vercel ejecuta `collectstatic` y los sirve desde su CDN.
- **Base de datos Neon**: en cada despliegue, `vercel_build.py` ejecuta `python manage.py preparar_produccion`:
  1. aplica las migraciones (con la conexión directa `DATABASE_URL_UNPOOLED`);
  2. importa el contenido (capítulos, diagnóstico, Base 20 y Plan 40) sin duplicar lo que ya existe;
  3. crea el administrador si definiste `DJANGO_SUPERUSER_USERNAME` y `DJANGO_SUPERUSER_PASSWORD`.
- La app en ejecución usa `DATABASE_URL` (con *pooler*), SSL obligatorio y sin cursores del servidor (requisito del pooler).
- Las grabaciones de voz se guardan en la base de datos, no en disco (el disco de Vercel se borra).

## 1. Subir el código a GitHub

En la carpeta del proyecto (la terminal ya debe estar en ella):

```
git init
git add .
git commit -m "Inglés para investigar y presentar: Base 20, Plan 40 y PWA"
git branch -M main
git remote add origin https://github.com/USUARIO/REPOSITORIO.git
git push -u origin main
```

- `.gitignore` deja fuera `.venv`, `db.sqlite3` (tus datos locales), `.env` (secretos) y `_to_delete`.
- Si el repositorio de GitHub ya tenía archivos (por ejemplo un README), antes del `push` ejecuta
  `git pull origin main --allow-unrelated-histories` y luego `git push -u origin main`.
- Revisa con `git status` que **no** aparezca `db.sqlite3` ni `.env`.

## 2. Crear el proyecto en Vercel

1. Entra a <https://vercel.com> → **Add New… → Project** → importa tu repositorio de GitHub.
2. *Framework Preset*: Vercel debería mostrar **Django** (si no, deja «Other»; igual lo detecta por `manage.py`).
3. **Antes de desplegar**, abre *Environment Variables* y agrega (para *Production* y *Preview*):

| Variable | Valor |
|---|---|
| `DJANGO_SECRET_KEY` | una clave larga; genérala con `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_SUPERUSER_USERNAME` | tu usuario administrador, por ejemplo `cesar` |
| `DJANGO_SUPERUSER_PASSWORD` | una contraseña segura (distinta de la local) |
| `DJANGO_SUPERUSER_EMAIL` | tu correo (opcional) |

## 3. Conectar la base de datos Neon

1. En el proyecto de Vercel: **Storage → Create Database → Neon (Postgres)** (o *Connect* si ya tienes una).
2. Elige una región cercana (por ejemplo `US East` o `São Paulo` si está disponible) y conéctala a *Production* y *Preview*.
3. Vercel agrega solo `DATABASE_URL` y `DATABASE_URL_UNPOOLED`. No las copies a ningún archivo del repositorio.

## 4. Desplegar

- **Deployments → Redeploy** (o haz un nuevo `git push`).
- En el registro de *Build* deberías ver: `1/3 Migraciones`, `2/3 Contenido … paquetes procesados`, `3/3 Administrador … creado` y `Producción lista.`
- Abre la URL `.vercel.app`, crea tu cuenta de alumno o entra con el administrador.

## 5. Instalar la app (PWA)

En la web aparece el botón **«Instalar la app»**, que se adapta al equipo:

| Equipo | Cómo se instala |
|---|---|
| Android (Chrome, Edge, Samsung) | botón **Instalar ahora** (aviso nativo) o menú ⋮ → *Instalar aplicación* |
| iPhone / iPad (Safari) | Compartir ⬆︎ → *Agregar a inicio* |
| iPhone con Chrome | Compartir ⬆︎ → *Agregar a pantalla de inicio* (si no aparece, usar Safari) |
| Windows / Linux / Chromebook (Chrome, Edge) | botón **Instalar ahora**; queda en el menú Inicio y se puede crear el acceso directo en el escritorio |
| Mac con Safari (macOS 14+) | Archivo → *Agregar al Dock* |
| Mac con Chrome / Edge | botón **Instalar ahora** (queda en Launchpad) |
| Firefox | indica abrir la página en Chrome, Edge o Safari |

Al ingresar se pregunta **«Mantener la sesión abierta en este equipo»**. En la app instalada la casilla aparece marcada
y con un aviso. Marcada: la sesión dura 90 días y se renueva con el uso. Sin marcar: se cierra al cerrar el navegador o la app.

## Problemas frecuentes

- **Build falla con «falta DATABASE_URL»**: conecta Neon (paso 3) y vuelve a desplegar.
- **Build falla con «falta DJANGO_SECRET_KEY»**: agrégala (paso 2.3) y vuelve a desplegar.
- **Error 500 al abrir**: Vercel → *Deployments* → el despliegue → *Logs*; el error completo aparece ahí.
- **Olvidaste la contraseña del administrador en producción**: cambia `DJANGO_SUPERUSER_PASSWORD`, agrega
  `DJANGO_SUPERUSER_RESET=1`, vuelve a desplegar y luego borra `DJANGO_SUPERUSER_RESET`.
- **Dominio propio**: agrégalo en Vercel → *Domains* y también en la variable `ALLOWED_HOSTS` (por ejemplo `ingles.midominio.cl`).
- **Preparar Neon desde tu computador** (opcional): en la terminal, `set DATABASE_URL=<la DATABASE_URL_UNPOOLED de Neon>`,
  `set DJANGO_SECRET_KEY=x` y luego `python manage.py preparar_produccion`. Cierra la terminal al terminar para no
  seguir apuntando a producción.

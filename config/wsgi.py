import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
# Vercel detecta Django por manage.py y usa WSGI_APPLICATION; `app` queda como alias.
app = application

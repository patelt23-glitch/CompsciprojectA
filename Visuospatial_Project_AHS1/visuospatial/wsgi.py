"""
WSGI config for visuospatial project.
Exposes the WSGI callable as both 'application' and 'app' for Vercel serverless deployment.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visuospatial.settings')

application = get_wsgi_application()
app = application

# Auto-initialize SQLite database when deploying to Vercel serverless functions
if os.environ.get('VERCEL'):
    try:
        from django.core.management import call_command
        call_command('migrate', interactive=False)
        call_command('seed_data')
    except Exception as e:
        print("Vercel startup migration notice:", e)

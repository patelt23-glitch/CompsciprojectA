#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
echo "Open http://127.0.0.1:8000/"
.venv/bin/python manage.py runserver 8000

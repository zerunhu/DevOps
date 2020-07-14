#!/bin/bash
#python manage.py collectstatic > /dev/null 2>&1 && \
#python manage.py makemigrations && \
#python manage.py migrate && \
gunicorn flashholdDevops.wsgi:application -c gunicorn.conf

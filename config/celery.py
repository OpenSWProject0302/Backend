import os
from celery import Celery

# Django settings 모듈 지정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Celery 앱 인스턴스 생성
celery = Celery("config")

# Django settings에서 CELERY_ 로 시작하는 설정 읽어오기
celery.config_from_object("django.conf:settings", namespace="CELERY")

# INSTALLED_APPS에 있는 모든 tasks.py 자동 검색
celery.autodiscover_tasks()

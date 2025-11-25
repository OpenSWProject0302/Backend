# jobs/urls.py
from django.urls import path
from .views import start_drum_job, get_drum_job

urlpatterns = [
    # POST /api/jobs/drums/start
    path("drums/start", start_drum_job),

    # GET /api/jobs/drums/<job_id>
    # DrumJob.id 가 UUIDField 이므로 uuid converter 사용
    path("drums/<uuid:job_id>", get_drum_job),
]

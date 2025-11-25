# jobs/views.py
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import DrumJob
from .tasks import run_drum_job


@api_view(["POST"])
def start_drum_job(request):
    """
    드럼 분석 Job 생성 API
    - 프론트에서 S3 업로드를 끝낸 뒤 호출
    - inputKey (필수), genre/tempo/level 등 옵션 전달
    - DrumJob 레코드를 만들고, Celery 작업을 비동기로 실행
    """
    data = request.data

    input_key = data.get("inputKey")
    genre = data.get("genre")
    tempo = data.get("tempo")
    level = data.get("level")

    # 기존 guest 쿠키 활용 (없으면 None)
    guest_id = request.COOKIES.get("guest_id")

    if not input_key:
        return Response(
            {"ok": False, "message": "inputKey is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # tempo를 안전하게 정수로 변환
    tempo_int = None
    if tempo is not None:
        try:
            tempo_int = int(tempo)
        except (TypeError, ValueError):
            return Response(
                {"ok": False, "message": "tempo must be integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    job = DrumJob.objects.create(
        guest_id=guest_id,
        input_key=input_key,
        genre=genre,
        tempo=tempo_int,
        level=level,
        status="PENDING",
    )

    # Celery 비동기 작업 실행
    run_drum_job.delay(str(job.id))

    return Response(
        {
            "ok": True,
            "jobId": str(job.id),
            "status": job.status,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def get_drum_job(request, job_id):
    """
    드럼 분석 Job 상태 조회 API
    - 프론트에서 폴링할 때 사용
    """
    job = get_object_or_404(DrumJob, pk=job_id)

    return Response(
        {
            "ok": True,
            "jobId": str(job.id),
            "status": job.status,
            "pdfKey": job.pdf_key,
            "audioKey": job.audio_key,
            "errorMessage": job.error_message,
            "createdAt": job.created_at,
            "updatedAt": job.updated_at,
        }
    )

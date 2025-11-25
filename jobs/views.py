# jobs/views.py
import boto3
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import DrumJob
from .tasks import run_drum_job

# S3 클라이언트
s3 = boto3.client("s3")
BUCKET = settings.AWS_STORAGE_BUCKET_NAME


@api_view(["POST"])
def start_drum_job(request):
    """
    드럼 분석 Job 생성 API
    - 프론트에서 S3 업로드를 끝낸 뒤 호출
    - inputKey (필수), genre/tempo/level 등 옵션 전달
    """
    data = request.data

    input_key = data.get("inputKey")
    genre = data.get("genre")
    tempo = data.get("tempo")
    level = data.get("level")
    guest_id = request.COOKIES.get("guest_id")

    if not input_key:
        return Response(
            {"ok": False, "message": "inputKey is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    job = DrumJob.objects.create(
        guest_id=guest_id,
        input_key=input_key,
        genre=genre,
        tempo=tempo or 0,
        level=level or "Normal",
        status="PENDING",
    )

    # Celery 비동기 작업 실행
    run_drum_job.delay(str(job.id))

    return Response(
        {
            "ok": True,
            "jobId": str(job.id),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def get_drum_job(request, job_id):
    """
    Job 상태 조회 API
    - status: PENDING / RUNNING / DONE / ERROR
    - DONE 이고 pdf_key / audio_key 가 있으면 presigned URL 생성해서 반환
    """
    job = get_object_or_404(DrumJob, pk=job_id)

    pdf_url = None
    audio_url = None

    if job.status == "DONE":
        if job.pdf_key:
            pdf_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET, "Key": job.pdf_key},
                ExpiresIn=600,  # 10분
            )
        if job.audio_key:
            audio_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET, "Key": job.audio_key},
                ExpiresIn=600,
            )

    return Response(
        {
            "ok": True,
            "jobId": str(job.id),
            "status": job.status,
            # 프론트에서 이미 pdfKey/audioKey를 쓰고 있을 테니 이름은 그대로 유지
            "pdfKey": pdf_url,
            "audioKey": audio_url,
            "errorMessage": job.error_message,
            "createdAt": job.created_at,
            "updatedAt": job.updated_at,
        }
    )

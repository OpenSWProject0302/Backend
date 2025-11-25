# jobs/views.py
import boto3
from botocore.config import Config
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import DrumJob
from .tasks import run_drum_job

# ── S3 클라이언트 (SigV4 강제) ─────────────────────────────────────
aws_region = getattr(settings, "AWS_S3_REGION_NAME", "ap-northeast-2")
aws_config = Config(signature_version="s3v4")

s3 = boto3.client("s3", region_name=aws_region, config=aws_config)
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
    - DONE 이면 S3 결과물 4개 (midi / pdf / guide / mix)에 대한 presigned URL 반환
    """
    job = get_object_or_404(DrumJob, pk=job_id)

    pdf_url = audio_url = midi_url = guide_url = None

    if job.status == "DONE":
        base_prefix = f"results/{job.id}"

        # 우리가 업로드한 실제 key 규칙
        midi_key = f"{base_prefix}/drums.mid"
        pdf_key = job.pdf_key or f"{base_prefix}/output.pdf"
        guide_key = f"{base_prefix}/guide.wav"
        mix_key = job.audio_key or f"{base_prefix}/mix.wav"

        pdf_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET,
                "Key": pdf_key,
                "ResponseContentDisposition": 'attachment; filename="easheet_score.pdf"',
            },
            ExpiresIn=600,
        )
        audio_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET,
                "Key": mix_key,
                "ResponseContentDisposition": 'attachment; filename="easheet_mix.wav"',
            },
            ExpiresIn=600,
        )
        midi_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET,
                "Key": midi_key,
                "ResponseContentDisposition": 'attachment; filename="easheet_drums.mid"',
            },
            ExpiresIn=600,
        )
        guide_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET,
                "Key": guide_key,
                "ResponseContentDisposition": 'attachment; filename="easheet_guide.wav"',
            },
            ExpiresIn=600,
        )

    return Response(
        {
            "ok": True,
            "jobId": str(job.id),
            "status": job.status,
            # 🔹 프론트에서 사용할 4가지 URL
            "pdfKey": pdf_url,
            "audioKey": audio_url,   # mix.wav
            "midiKey": midi_url,
            "guideKey": guide_url,
            "errorMessage": job.error_message,
            "createdAt": job.created_at,
            "updatedAt": job.updated_at,
        }
    )

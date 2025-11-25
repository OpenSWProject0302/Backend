# jobs/tasks.py
import logging
import tempfile
from pathlib import Path

import boto3
from celery import shared_task
from django.conf import settings

from .models import DrumJob
from drum.pipeline import run_drum_pipeline  # drum/pipeline.py 의 함수

logger = logging.getLogger(__name__)

# S3 클라이언트
s3 = boto3.client("s3")
BUCKET = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)


def build_s3_url(key: str) -> str:
    """
    S3 object key -> 브라우저에서 접근 가능한 URL로 변환
    """
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    region = getattr(settings, "AWS_S3_REGION_NAME", None)

    if bucket and region:
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
    elif bucket:
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return key


@shared_task
def run_drum_job(job_id: str):
    """
    Celery 비동기 Job

    1) S3에서 입력 wav 다운로드 (job.input_key)
    2) run_drum_pipeline 실행 (PDF/오디오 생성)
    3) 결과 파일들을 S3 results/ 경로에 업로드
    4) DrumJob.status / pdf_key / audio_key 업데이트
    """
    job = DrumJob.objects.get(pk=job_id)

    job.status = "RUNNING"
    job.save()

    if not BUCKET:
        msg = "AWS_STORAGE_BUCKET_NAME is not set in settings."
        logger.error("[DrumJob] %s", msg)
        job.status = "ERROR"
        job.error_message = msg
        job.save()
        return

    try:
        logger.info("[DrumJob] START job_id=%s, input_key=%s", job_id, job.input_key)

        # 1) 임시 디렉터리 생성
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"drumjob_{job_id}_"))
        logger.info("[DrumJob] tmp_dir=%s", tmp_dir)

        # 2) S3에서 입력 오디오 다운로드
        input_filename = Path(job.input_key).name or "input.wav"
        local_input_path = tmp_dir / input_filename

        logger.info(
            "[DrumJob] Downloading from S3 bucket=%s key=%s -> %s",
            BUCKET,
            job.input_key,
            local_input_path,
        )
        s3.download_file(BUCKET, job.input_key, str(local_input_path))

        # 3) 파이프라인 실행 (로컬에서 MIDI/PDF/오디오 생성)
        result_paths = run_drum_pipeline(
            audio_path=local_input_path,
            genre=job.genre or "Rock",
            tempo=job.tempo or 120,
            level=job.level or "Normal",
            output_dir=tmp_dir,
        )

        logger.info("[DrumJob] PIPELINE RESULT paths=%s", result_paths)

        pdf_path = Path(result_paths["pdf"])
        audio_path = Path(result_paths.get("mix_audio") or result_paths["drum_audio"])

        # 4) 결과물 S3 key 정의
        pdf_key = f"results/{job.id}/output.pdf"
        audio_key = f"results/{job.id}/output.wav"

        # 5) 결과물 S3 업로드
        logger.info(
            "[DrumJob] Uploading PDF to S3 bucket=%s key=%s from %s",
            BUCKET,
            pdf_key,
            pdf_path,
        )
        s3.upload_file(str(pdf_path), BUCKET, pdf_key)

        logger.info(
            "[DrumJob] Uploading audio to S3 bucket=%s key=%s from %s",
            BUCKET,
            audio_key,
            audio_path,
        )
        s3.upload_file(str(audio_path), BUCKET, audio_key)

        # 6) DB에 URL 저장 (프론트가 그대로 href로 사용 가능하도록)
        job.pdf_key = build_s3_url(pdf_key)
        job.audio_key = build_s3_url(audio_key)
        job.status = "DONE"

        logger.info(
            "[DrumJob] DONE job_id=%s pdf_url=%s audio_url=%s",
            job_id,
            job.pdf_key,
            job.audio_key,
        )

    except Exception as e:
        logger.exception("[DrumJob] ERROR job_id=%s: %s", job_id, e)
        job.status = "ERROR"
        job.error_message = str(e)

    job.save()

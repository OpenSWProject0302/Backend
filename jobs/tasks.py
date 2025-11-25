# jobs/tasks.py
import logging
import tempfile
import shutil
from pathlib import Path

import boto3
from celery import shared_task
from django.conf import settings
from botocore.config import Config

from .models import DrumJob
from drum.pipeline import run_drum_pipeline  # drum/pipeline.py

logger = logging.getLogger(__name__)


aws_region = getattr(settings, "AWS_S3_REGION_NAME", "ap-northeast-2")
aws_config = Config(signature_version="s3v4")

s3 = boto3.client("s3", region_name=aws_region, config=aws_config)
BUCKET = settings.AWS_STORAGE_BUCKET_NAME



@shared_task
def run_drum_job(job_id: str):
    """
    Celery 비동기 작업.

    1) S3에서 입력 wav 다운로드 (job.input_key)
    2) run_drum_pipeline 실행 → midi / pdf / guide wav / mix wav 생성
    3) 결과물 4개를 S3의 results/{job_id}/ 아래에 업로드
    4) DrumJob에는 "S3 key" 만 저장 (URL X), status="DONE"
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

    tmp_dir: Path | None = None

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

        # 3) 파이프라인 실행 (로컬에서 MIDI/PDF/오디오 2개 생성)
        result_paths = run_drum_pipeline(
            audio_path=local_input_path,
            genre=job.genre or "Rock",
            tempo=job.tempo or 120,
            level=job.level or "Normal",
            output_dir=tmp_dir,
        )

        logger.info("[DrumJob] PIPELINE RESULT paths=%s", result_paths)

        midi_path = Path(result_paths["midi"])
        pdf_path = Path(result_paths["pdf"])
        guide_audio_path = Path(result_paths["drum_audio"])  # 가이드 드럼만
        mix_audio_path = Path(result_paths["mix_audio"])     # 원곡+드럼 믹스

        # 4) S3 key 정의 (총 4개)
        base_prefix = f"results/{job.id}"
        midi_key = f"{base_prefix}/drums.mid"
        pdf_key = f"{base_prefix}/output.pdf"
        guide_audio_key = f"{base_prefix}/guide.wav"
        mix_audio_key = f"{base_prefix}/mix.wav"

        # 5) 결과물 4개 모두 업로드
        logger.info("[DrumJob] Uploading MIDI to S3 key=%s", midi_key)
        s3.upload_file(str(midi_path), BUCKET, midi_key)

        logger.info("[DrumJob] Uploading PDF to S3 key=%s", pdf_key)
        s3.upload_file(
            str(pdf_path),
            BUCKET,
            pdf_key,
            ExtraArgs={"ContentType": "application/pdf"},
        )

        logger.info("[DrumJob] Uploading GUIDE audio to S3 key=%s", guide_audio_key)
        s3.upload_file(
            str(guide_audio_path),
            BUCKET,
            guide_audio_key,
            ExtraArgs={"ContentType": "audio/wav"},
        )

        logger.info("[DrumJob] Uploading MIX audio to S3 key=%s", mix_audio_key)
        s3.upload_file(
            str(mix_audio_path),
            BUCKET,
            mix_audio_key,
            ExtraArgs={"ContentType": "audio/wav"},
        )

        # 6) DB에는 "S3 key" 만 저장 (URL X)
        #    프론트에서 실제 다운로드 URL은 presigned URL 로 따로 발급
        job.pdf_key = pdf_key          # output.pdf
        job.audio_key = mix_audio_key  # mix.wav (사용자한테 내려줄 오디오)

        job.status = "DONE"
        job.error_message = ""

        logger.info(
            "[DrumJob] DONE job_id=%s pdf_key=%s audio_key=%s",
            job_id,
            job.pdf_key,
            job.audio_key,
        )

    except Exception as e:
        logger.exception("[DrumJob] ERROR job_id=%s: %s", job_id, e)
        job.status = "ERROR"
        job.error_message = str(e)

    finally:
        # ✅ 임시 폴더 정리 (성공/실패 상관없이)
        if tmp_dir and tmp_dir.exists():
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                logger.info("[DrumJob] tmp_dir removed: %s", tmp_dir)
            except Exception as e:
                logger.warning("[DrumJob] tmp_dir cleanup failed %s: %s", tmp_dir, e)

        job.save()

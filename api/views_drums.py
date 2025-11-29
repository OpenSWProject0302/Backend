from __future__ import annotations

import json
import uuid
from pathlib import Path

import logging
from threading import Thread

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .utils_s3 import (
    download_from_s3_to_temp_path,
    upload_file_and_presign,
)
from drum.pipeline import run_drum_pipeline
from jobs.models import DrumJob

logger = logging.getLogger(__name__)


@csrf_exempt  # 개발 단계용
@require_POST
def process_drum(request):
    # 1. guest_id 쿠키 확인
    guest_id = request.COOKIES.get("guest_id")
    if not guest_id:
        return JsonResponse(
            {"ok": False, "error": "GUEST_NOT_INITIALIZED"},
            status=400,
        )

    # 2. body 파싱
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {"ok": False, "error": "INVALID_JSON"},
            status=400,
        )

    input_key = body.get("inputKey")
    genre = body.get("genre")
    tempo = body.get("tempo")
    level = body.get("level")

    if not input_key or not isinstance(input_key, str):
        return JsonResponse(
            {"ok": False, "error": "INPUT_KEY_REQUIRED"},
            status=400,
        )

    if not (genre and level and tempo):
        return JsonResponse(
            {"ok": False, "error": "MISSING_FIELDS"},
            status=400,
        )

    try:
        tempo = int(tempo)
    except (TypeError, ValueError):
        return JsonResponse(
            {"ok": False, "error": "INVALID_TEMPO"},
            status=400,
        )

    # 3. inputKey가 내 guest 영역인지 확인
    expected_prefix = f"uploads/{guest_id}/"
    if not input_key.startswith(expected_prefix):
        return JsonResponse(
            {"ok": False, "error": "FORBIDDEN_INPUT_KEY"},
            status=403,
        )

    # 4. S3 → 임시 파일(Path) 다운로드
    try:
        local_audio_path: Path = download_from_s3_to_temp_path(input_key)
    except Exception as e:
        return JsonResponse(
            {"ok": False, "error": "S3_DOWNLOAD_FAILED", "detail": str(e)},
            status=500,
        )

    # 5. 파이프라인 실행
    try:
        # run_drum_pipeline 이 dict[str, Path | str] 을 리턴한다고 가정
        outputs = run_drum_pipeline(
            audio_path=local_audio_path,
            genre=genre,
            tempo=tempo,
            level=level,
            output_dir=None,
        )
    except Exception as e:
        return JsonResponse(
            {"ok": False, "error": "PIPELINE_FAILED", "detail": str(e)},
            status=500,
        )

    # 6. 결과 파일들을 S3에 업로드 + presigned URL 생성
    job_id = uuid.uuid4().hex
    base_prefix = f"results/{guest_id}/{job_id}/"

    result_map: dict[str, dict] = {}

    for kind, local_path in outputs.items():
        local_path = Path(local_path)
        key = f"{base_prefix}{local_path.name}"

        try:
            info = upload_file_and_presign(local_path, key, expires_in=600)
        except Exception as e:
            return JsonResponse(
                {"ok": False, "error": "S3_UPLOAD_FAILED", "detail": str(e)},
                status=500,
            )

        # contentType 추론
        suffix = local_path.suffix.lower()
        if suffix in [".mid", ".midi"]:
            content_type = "audio/midi"
        elif suffix in [".mp3", ".wav"]:
            content_type = "audio/mpeg"
        elif suffix == ".pdf":
            content_type = "application/pdf"
        else:
            content_type = "application/octet-stream"

        result_map[kind] = {
            **info,  # key, url, filename
            "contentType": content_type,
        }

    return JsonResponse(
        {
            "ok": True,
            "jobId": job_id,
            "results": result_map,
        },
        status=200,
    )


def _run_drum_job_in_background(job_id: str):

    # 오래 걸리는 드럼 파이프라인을 백그라운드에서 실행하는 함수. (별도 Thread 에서 실행)

    from django.db import connection  # 쓰고 끝에 close 해주기 위해

    try:
        job = DrumJob.objects.get(id=job_id)
        job.status = "RUNNING"
        job.save(update_fields=["status", "updated_at"])

        # 실제 드럼 파이프라인 호출
        result = run_drum_pipeline(
            input_key=job.input_key,
            genre=job.genre,
            tempo=job.tempo,
            level=job.level,
        )
        # result 안에 pdf/audio S3 key 를 반환
        job.pdf_key = result.get("pdf_key")
        job.audio_key = result.get("audio_key")
        job.status = "DONE"
        job.error_message = ""
        job.save(update_fields=["pdf_key", "audio_key", "status", "error_message", "updated_at"])

    except Exception as e:
        logger.exception("Drum job %s failed", job_id)
        try:
            job = DrumJob.objects.get(id=job_id)
            job.status = "ERROR"
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            logger.exception("Failed to save error status for job %s", job_id)
    finally:
        # Thread 안에서 DB 커넥션 정리
        connection.close()

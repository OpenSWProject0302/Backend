# api/views_drums.py
from __future__ import annotations

import json
import uuid
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .utils_s3 import (
    download_from_s3_to_temp,
    upload_file_to_s3,
    create_presigned_get_url,
)
from drum.pipeline import run_drum_pipeline


@csrf_exempt  # 개발 단계용 (나중에 CSRF 헤더 붙이면 제거)
@require_POST
def process_drum(request):
    # 1. guest_id 쿠키 확인
    guest_id = request.COOKIES.get("guest_id")
    if not guest_id:
        return JsonResponse({"ok": False, "error": "GUEST_NOT_INITIALIZED"}, status=400)

    # 2. body 파싱
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "INVALID_JSON"}, status=400)

    input_key = body.get("inputKey")
    genre = body.get("genre")
    tempo = body.get("tempo")
    level = body.get("level")

    if not input_key or not isinstance(input_key, str):
        return JsonResponse({"ok": False, "error": "INPUT_KEY_REQUIRED"}, status=400)

    if not (genre and level and tempo):
        return JsonResponse({"ok": False, "error": "MISSING_FIELDS"}, status=400)

    try:
        tempo = int(tempo)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "INVALID_TEMPO"}, status=400)

    # 3. inputKey가 내 guest 영역인지 확인
    expected_prefix = f"uploads/{guest_id}/"
    if not input_key.startswith(expected_prefix):
        return JsonResponse({"ok": False, "error": "FORBIDDEN_INPUT_KEY"}, status=403)

    # 4. S3 → 임시 파일 다운로드
    local_audio_path = download_from_s3_to_temp(input_key)

    # 5. 파이프라인 실행
    try:
        outputs = run_drum_pipeline(
            audio_path=local_audio_path,
            genre=genre,
            tempo=tempo,
            level=level,
            output_dir=None,
        )
    except Exception as e:
        # TODO: logging 추가 가능
        return JsonResponse(
            {"ok": False, "error": "PIPELINE_FAILED", "detail": str(e)}, status=500
        )

    # 6. 결과 파일들을 S3에 업로드
    job_id = uuid.uuid4().hex
    base_prefix = f"results/{guest_id}/{job_id}/"

    result_map = {}
    for kind, local_path in outputs.items():
        local_path = Path(local_path)
        key = f"{base_prefix}{local_path.name}"

        upload_file_to_s3(str(local_path), key)
        url = create_presigned_get_url(key, expires_in=600)

        if local_path.suffix.lower() in [".mid", ".midi"]:
            content_type = "audio/midi"
        elif local_path.suffix.lower() in [".mp3", ".wav"]:
            content_type = "audio/mpeg"
        elif local_path.suffix.lower() == ".pdf":
            content_type = "application/pdf"
        else:
            content_type = "application/octet-stream"

        result_map[kind] = {
            "key": key,
            "url": url,
            "filename": local_path.name,
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

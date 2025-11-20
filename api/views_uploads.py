import json
import uuid

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import boto3
from pathlib import Path


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


# 브라우저마다 wav MIME 타입이 조금씩 다를 수 있어서 넉넉하게 허용
ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",     # 일반 mp3
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/x-wave",
}

ALLOWED_EXTS = {".mp3", ".wav"}


@csrf_exempt
@require_POST
def upload_presign(request):
    # 1) guest_id 쿠키 확인
    guest_id = request.COOKIES.get("guest_id")
    if not guest_id:
        return JsonResponse(
            {"ok": False, "error": "GUEST_NOT_INITIALIZED"},
            status=400,
        )

    # 2) JSON 파싱
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {"ok": False, "error": "INVALID_JSON"},
            status=400,
        )

    filename = body.get("filename") or "upload.bin"
    size = body.get("size")
    content_type = body.get("contentType")

    # size가 문자열로 들어와도 int로 변환 시도
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = -1

    # 3) 기본 검증 (size, contentType)
    if size <= 0 or size > settings.MAX_UPLOAD_SIZE:
        return JsonResponse(
            {"ok": False, "error": "INVALID_SIZE"},
            status=400,
        )

    if content_type not in ALLOWED_CONTENT_TYPES:
        return JsonResponse(
            {"ok": False, "error": "INVALID_CONTENT_TYPE"},
            status=400,
        )

    # 4) 파일 확장자 추출 및 검증
    ext = Path(filename).suffix.lower()
    if ext == "":
        ext = ".bin"

    if ext not in ALLOWED_EXTS:
        return JsonResponse(
            {"ok": False, "error": "UNSUPPORTED_EXTENSION"},
            status=400,
        )

    # 5) S3 키 규칙: uploads/{guest_id}/{UUID}{ext}
    key = f"uploads/{guest_id}/{uuid.uuid4().hex}{ext}"

    s3 = get_s3_client()
    bucket = settings.AWS_S3_BUCKET_NAME
    expires_in = 300  # 5분

    try:
        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
    except Exception:
        return JsonResponse(
            {"ok": False, "error": "PRESIGN_FAILED"},
            status=500,
        )

    return JsonResponse(
        {
            "ok": True,
            "uploadUrl": upload_url,
            "key": key,
            "expiresIn": expires_in,
        }
    )

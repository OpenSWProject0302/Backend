from __future__ import annotations

import os
import tempfile
from pathlib import Path

import boto3
from django.conf import settings


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def download_from_s3_to_temp(key: str, suffix: str | None = None) -> str:
    """
    S3 객체를 임시 파일로 다운로드하고 로컬 경로(문자열)를 반환.
    """
    s3 = get_s3_client()
    bucket = settings.AWS_S3_BUCKET_NAME

    # key에 확장자가 있으면 그대로 suffix로 사용
    if suffix is None:
        _, dot, ext = key.rpartition(".")
        suffix = f".{ext}" if dot and ext else ""

    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    s3.download_file(bucket, key, tmp_path)
    return tmp_path


def download_from_s3_to_temp_path(key: str, suffix: str | None = None) -> Path:
    """
    위 함수의 Path 버전. 파이프라인 코드에서 Path 객체로 쓰기 좋게 래핑.
    """
    return Path(download_from_s3_to_temp(key, suffix=suffix))


def upload_file_to_s3(local_path: str | Path, key: str) -> None:
    """
    로컬 파일을 S3에 업로드.
    """
    s3 = get_s3_client()
    bucket = settings.AWS_S3_BUCKET_NAME
    s3.upload_file(str(local_path), bucket, key)


def create_presigned_get_url(key: str, expires_in: int = 600) -> str:
    """
    S3 객체에 대한 다운로드용 presigned URL 생성.
    """
    s3 = get_s3_client()
    bucket = settings.AWS_S3_BUCKET_NAME
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def upload_file_and_presign(
    local_path: str | Path,
    key: str,
    expires_in: int = 600,
) -> dict[str, str]:
    """
    로컬 파일을 S3에 업로드하고, 곧바로 presigned GET URL까지 생성해서
    { key, url, filename } 형태로 반환.
    """
    local_path = Path(local_path)

    # 1) 업로드
    upload_file_to_s3(local_path, key)

    # 2) presigned URL 생성
    url = create_presigned_get_url(key, expires_in=expires_in)

    return {
        "key": key,
        "url": url,
        "filename": local_path.name,
    }

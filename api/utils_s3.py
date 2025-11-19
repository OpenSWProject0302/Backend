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
    S3 객체를 임시 파일로 다운로드하고 로컬 경로를 반환.
    """
    s3 = get_s3_client()
    bucket = settings.AWS_S3_BUCKET_NAME

    if suffix is None:
        _, dot, ext = key.rpartition(".")
        suffix = f".{ext}" if dot and ext else ""

    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    s3.download_file(bucket, key, tmp_path)
    return tmp_path


def upload_file_to_s3(local_path: str, key: str):
    s3 = get_s3_client()
    bucket = settings.AWS_S3_BUCKET_NAME
    s3.upload_file(local_path, bucket, key)


def create_presigned_get_url(key: str, expires_in: int = 600) -> str:
    s3 = get_s3_client()
    bucket = settings.AWS_S3_BUCKET_NAME
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )

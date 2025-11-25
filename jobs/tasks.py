# jobs/tasks.py
from celery import shared_task

from .models import DrumJob

# 실제 파이프라인 함수는 네 프로젝트 구조에 맞게 import
# 예시: pipeline.py 에 run_drum_pipeline 이 있다고 가정
# from pipeline import run_drum_pipeline


@shared_task
def run_drum_job(job_id: str):
    """
    Celery가 실행하는 실제 비동기 작업.
    - S3에서 wav 가져오기
    - 분석 / 변환
    - 결과물 S3에 업로드
    - DrumJob 상태/결과 업데이트
    """
    job = DrumJob.objects.get(pk=job_id)

    job.status = "RUNNING"
    job.save()

    try:
        # TODO: 여기를 실제 파이프라인에 맞게 구현하면 됨.
        # 예시)
        # pdf_key, audio_key = run_drum_pipeline(
        #     input_key=job.input_key,
        #     genre=job.genre,
        #     tempo=job.tempo,
        #     level=job.level,
        # )

        # 일단 개발 단계에서는 더미 값으로 넣어도 됨.
        pdf_key = f"results/{job.id}/output.pdf"
        audio_key = f"results/{job.id}/preview.wav"

        job.pdf_key = pdf_key
        job.audio_key = audio_key
        job.status = "DONE"

    except Exception as e:
        job.status = "ERROR"
        job.error_message = str(e)

    job.save()

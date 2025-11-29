import uuid
from django.db import models


class DrumJob(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("RUNNING", "Running"),
        ("DONE", "Done"),
        ("ERROR", "Error"),
    ]

    # UUID 기반 PK
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 게스트 쿠키
    guest_id = models.CharField(max_length=64, blank=True, null=True)

    # 입력 wav S3 key
    input_key = models.CharField(max_length=255)

    genre = models.CharField(max_length=64, blank=True, null=True)
    tempo = models.IntegerField(blank=True, null=True)
    level = models.CharField(max_length=16, blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    # 결과물 S3 key
    pdf_key = models.CharField(max_length=255, blank=True, null=True)
    audio_key = models.CharField(max_length=255, blank=True, null=True)

    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"DrumJob({self.id}) - {self.status}"

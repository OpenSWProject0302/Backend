import uuid
from django.http import JsonResponse
from django.conf import settings  # DEBUG 모드 확인을 위해 추가


def guest_init(request):
    guest_id = request.COOKIES.get("guest_id")
    if not guest_id:
        guest_id = uuid.uuid4().hex

    resp = JsonResponse({"ok": True, "guestId": guest_id})

    # 배포 환경(Vercel <-> EC2) 간 쿠키 공유를 위한 설정
    resp.set_cookie(
        "guest_id",
        guest_id,
        httponly=True,
        # 배포(DEBUG=False)일 때는 True(HTTPS 필수), 개발(DEBUG=True)일 때는 False
        secure=True if not settings.DEBUG else False,
        # 배포 시엔 "None"으로 해야 크로스 도메인 허용, 개발 땐 "Lax"가 편함
        samesite="None" if not settings.DEBUG else "Lax",
        max_age=60 * 60 * 24 * 90,
    )
    return resp
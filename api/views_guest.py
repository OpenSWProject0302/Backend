import uuid
from django.http import JsonResponse

def guest_init(request):
    guest_id = request.COOKIES.get("guest_id")
    if not guest_id:
        guest_id = uuid.uuid4().hex

    resp = JsonResponse({"ok": True, "guestId": guest_id})
    resp.set_cookie(
        "guest_id",
        guest_id,
        httponly=True,
        secure=False,      # 로컬 개발은 False, 배포 시 True로
        samesite="Lax",
        max_age=60 * 60 * 24 * 90,
    )
    return resp
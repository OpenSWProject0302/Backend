from django.urls import path
from .views_guest import guest_init
from .views_uploads import upload_presign

urlpatterns = [
    path("guest/init", guest_init),
    path("uploads/presign", upload_presign, name="upload-presign"),

]
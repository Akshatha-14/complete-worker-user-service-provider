from django.contrib import admin
from django.urls import path, include
from core.admin import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ✅ Use your custom admin site (this enables /custom-admin/dashboard/)
    path("admin/", admin.site.urls),

    # ✅ Your backend API routes
    path("api/", include("core.urls")),

    # (Optional) keep the default admin only if you still need it for debugging
    # path("admin/", admin.site.urls),
    
]

# ✅ Serve uploaded media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

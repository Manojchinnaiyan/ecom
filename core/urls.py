from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# API versions
API_V1 = "api/v1/"

urlpatterns = [
    # Admin site
    path("admin/", admin.site.urls),
    # API endpoints
    path(f"{API_V1}accounts/", include("apps.accounts.api.urls")),
    path(f"{API_V1}products/", include("apps.products.api.urls")),
    path(f"{API_V1}orders/", include("apps.orders.api.urls")),
    path(f"{API_V1}payments/", include("apps.payments.api.urls")),
    path(f"{API_V1}recommendations/", include("apps.recommendations.api.urls")),
    # Optional: Browser-based API authentication
    path("api-auth/", include("rest_framework.urls")),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

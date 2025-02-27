from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from rest_framework.documentation import include_docs_urls

# API versions
API_V1 = "api/v1/"

urlpatterns = [
    # Admin site
    path("admin/", admin.site.urls),
    # API Documentation
    path(
        "docs/",
        include_docs_urls(title="E-Commerce API", description="API Documentation"),
    ),
    # API endpoints
    path(f"{API_V1}accounts/", include("accounts.api.urls")),
    path(f"{API_V1}products/", include("products.api.urls")),
    path(f"{API_V1}orders/", include("orders.api.urls")),
    path(f"{API_V1}payments/", include("payments.api.urls")),
    path(f"{API_V1}recommendations/", include("recommendations.api.urls")),
    # Optional: Browser-based API authentication
    path("api-auth/", include("rest_framework.urls")),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = "ecom.views.handler404"
handler500 = "ecom.views.handler500"

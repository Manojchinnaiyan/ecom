# apps/products/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ProductViewSet,
    ProductImageViewSet,
    ProductVariantViewSet,
    ProductReviewViewSet,
    InventoryViewSet,
)

# Create a router for viewsets
router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"images", ProductImageViewSet, basename="product-image")
router.register(r"variants", ProductVariantViewSet, basename="product-variant")
router.register(r"reviews", ProductReviewViewSet, basename="product-review")
router.register(r"inventory", InventoryViewSet, basename="inventory")

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
]

# apps/orders/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    OrderViewSet,
    OrderItemViewSet,
    CartViewSet,
    CartItemViewSet,
    CouponViewSet,
)

# Create a router for viewsets
router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"order-items", OrderItemViewSet, basename="order-item")
router.register(r"carts", CartViewSet, basename="cart")
router.register(r"cart-items", CartItemViewSet, basename="cart-item")
router.register(r"coupons", CouponViewSet, basename="coupon")

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
]

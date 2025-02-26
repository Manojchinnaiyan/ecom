# apps/payments/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PaymentViewSet,
    RefundViewSet,
    PaymentMethodViewSet,
    InvoiceViewSet,
    TransactionViewSet,
)

# Create a router for viewsets
router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"refunds", RefundViewSet, basename="refund")
router.register(r"payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
]

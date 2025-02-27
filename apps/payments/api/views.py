# apps/payments/api/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.payments.models import Payment, Refund, PaymentMethod, Invoice, Transaction
from .serializers import (
    PaymentSerializer,
    RefundSerializer,
    PaymentMethodSerializer,
    InvoiceSerializer,
    TransactionSerializer,
    PaymentCreateSerializer,
    RefundCreateSerializer,
)
from utils.permissions import IsOwnerOrAdmin


class PaymentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for payments.
    """

    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["order", "status", "payment_method"]
    ordering_fields = ["created_at", "amount"]

    def get_serializer_class(self):
        """
        Return different serializers for create vs other actions.
        """
        if self.action == "create":
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_queryset(self):
        """
        Return payments for the current user or all payments for staff.
        """
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(order__user=self.request.user)


class RefundViewSet(viewsets.ModelViewSet):
    """
    API endpoint for refunds.
    """

    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["order", "payment", "status", "reason"]
    ordering_fields = ["created_at", "amount"]

    def get_serializer_class(self):
        """
        Return different serializers for create vs other actions.
        """
        if self.action == "create":
            return RefundCreateSerializer
        return RefundSerializer

    def get_queryset(self):
        """
        Return refunds for the current user or all refunds for staff.
        """
        if self.request.user.is_staff:
            return Refund.objects.all()
        return Refund.objects.filter(order__user=self.request.user)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    API endpoint for payment methods.
    """

    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Return payment methods for the current user or all for staff.
        """
        if self.request.user.is_staff:
            return PaymentMethod.objects.all()
        return PaymentMethod.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        """
        Set a payment method as default.
        """
        payment_method = self.get_object()
        payment_method.is_default = True
        payment_method.save()

        return Response(
            {"status": "success", "detail": "Payment method set as default"}
        )


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for invoices (read-only for regular users).
    """

    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["order", "status"]
    ordering_fields = ["created_at", "due_date"]

    def get_queryset(self):
        """
        Return invoices for the current user's orders or all for staff.
        """
        if self.request.user.is_staff:
            return Invoice.objects.all()
        return Invoice.objects.filter(order__user=self.request.user)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """
        Download invoice PDF.
        """
        invoice = self.get_object()

        if not invoice.invoice_pdf:
            return Response(
                {"status": "error", "detail": "No PDF available for this invoice"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # In a real application, you would serve the PDF file
        # This is a placeholder response
        return Response(
            {
                "status": "success",
                "detail": "PDF download link",
                "url": request.build_absolute_uri(invoice.invoice_pdf.url),
            }
        )


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for transactions (read-only).
    """

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["order", "transaction_type", "payment", "refund"]
    ordering_fields = ["created_at", "amount"]

    def get_queryset(self):
        """
        Return transactions for the current user or all for staff.
        """
        if self.request.user.is_staff:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)

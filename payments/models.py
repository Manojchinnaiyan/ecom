from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("partially_refunded", "Partially Refunded"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cash_on_delivery", "Cash on Delivery"),
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("paypal", "PayPal"),
        ("bank_transfer", "Bank Transfer"),
        ("stripe", "Stripe"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    currency = models.CharField(max_length=3, default="USD")
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    payment_gateway = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.order_number}"


class Refund(models.Model):
    REFUND_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    ]

    REFUND_REASON_CHOICES = [
        ("duplicate", "Duplicate"),
        ("defective", "Defective"),
        ("wrong_item", "Wrong Item"),
        ("not_as_described", "Not as Described"),
        ("late_delivery", "Late Delivery"),
        ("fraudulent", "Fraudulent"),
        ("customer_request", "Customer Request"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="refunds"
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="refunds"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=REFUND_STATUS_CHOICES, default="pending"
    )
    reason = models.CharField(
        max_length=20, choices=REFUND_REASON_CHOICES, default="other"
    )
    notes = models.TextField(blank=True, null=True)

    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Refund"
        verbose_name_plural = "Refunds"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.id} for Order {self.order.order_number} and Payment {self.payment.id}"


class PaymentMethod(models.Model):
    """
    Saved payment methods for users.
    """

    PAYMENT_TYPE_CHOICES = [
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("paypal", "PayPal"),
        ("bank_account", "Bank Account"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="payment_methods"
    )

    # Payment method details
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    is_default = models.BooleanField(default=False)

    # Card specific fields (encrypted or tokenized in production)
    card_last4 = models.CharField(max_length=4, blank=True, null=True)
    card_expiry_month = models.PositiveSmallIntegerField(blank=True, null=True)
    card_expiry_year = models.PositiveSmallIntegerField(blank=True, null=True)
    card_brand = models.CharField(max_length=50, blank=True, null=True)

    # External references
    gateway_token = models.CharField(max_length=255, blank=True, null=True)
    gateway_customer_id = models.CharField(max_length=255, blank=True, null=True)

    # Billing address
    billing_address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        related_name="payment_methods",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("payment method")
        verbose_name_plural = _("payment methods")

    def __str__(self):
        if self.payment_type in ["credit_card", "debit_card"] and self.card_last4:
            return f"{self.get_payment_type_display()} ending in {self.card_last4}"
        return self.get_payment_type_display()

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other payment methods for this user to non-default
            PaymentMethod.objects.filter(user=self.user, is_default=True).exclude(
                id=self.id
            ).update(is_default=False)
        super().save(*args, **kwargs)


class Invoice(models.Model):
    INVOICE_STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("canceled", "Canceled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="invoice"
    )
    invoice_number = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20, choices=INVOICE_STATUS_CHOICES, default="draft"
    )
    due_date = models.DateField(blank=True, null=True)
    tax_id = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    invoice_pdf = models.FileField(upload_to="invoices/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"Invoice {self.invoice_number} for Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from django.utils import timezone

            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """
    Detailed transaction log for all financial activities.
    """

    TRANSACTION_TYPE_CHOICES = [
        ("payment", "Payment"),
        ("refund", "Refund"),
        ("chargeback", "Chargeback"),
        ("adjustment", "Adjustment"),
        ("fee", "Fee"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="transactions",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        related_name="transactions",
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    refund = models.ForeignKey(
        Refund,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )

    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    description = models.TextField(blank=True, null=True)

    # External references
    external_id = models.CharField(max_length=255, blank=True, null=True)
    gateway = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    # Timestamps and metadata
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        verbose_name = _("transaction")
        verbose_name_plural = _("transactions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} Transaction {self.id}"

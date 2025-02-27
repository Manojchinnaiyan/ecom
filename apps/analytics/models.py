from django.db import models

# Create your models here.
# 2. Analytics and Reporting System
# apps/analytics/models.py
from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _


class ProductPerformance(models.Model):
    """
    Model to store aggregated product performance metrics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        "products.Product", on_delete=models.CASCADE, related_name="performance"
    )

    # Sales metrics
    total_sales = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    # Conversion metrics
    views = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    conversion_rate = models.FloatField(default=0)  # percentage

    # Customer metrics
    unique_customers = models.PositiveIntegerField(default=0)
    repeat_purchase_rate = models.FloatField(default=0)  # percentage

    # Review metrics
    review_count = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0)

    # Timeframe
    start_date = models.DateField()
    end_date = models.DateField()

    # Last updated
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("product performance")
        verbose_name_plural = _("product performances")
        indexes = [
            models.Index(fields=["-total_revenue"]),
            models.Index(fields=["-conversion_rate"]),
            models.Index(fields=["-average_rating"]),
        ]


class SalesByPeriod(models.Model):
    """
    Model to store aggregated sales data by period.
    """

    PERIOD_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()

    # Sales metrics
    order_count = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    item_count = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Customer metrics
    new_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)

    # Updated at
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("sales by period")
        verbose_name_plural = _("sales by periods")
        unique_together = ("period_type", "period_start", "period_end")
        indexes = [
            models.Index(fields=["period_type", "period_start"]),
        ]

from django.db import models

# Create your models here.
# 1. Product Recommendations Engine
# apps/recommendations/models.py
from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _


class ProductAssociation(models.Model):
    """
    Model to store product associations for recommendations.
    """

    ASSOCIATION_TYPES = [
        ("bought_together", "Frequently Bought Together"),
        ("viewed_together", "Frequently Viewed Together"),
        ("complementary", "Complementary Products"),
        ("upsell", "Upsell Products"),
        ("cross_sell", "Cross-sell Products"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="source_associations"
    )
    target_product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="target_associations"
    )
    association_type = models.CharField(max_length=20, choices=ASSOCIATION_TYPES)
    strength = models.FloatField(default=0.0)  # Score between 0 and 1
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("product association")
        verbose_name_plural = _("product associations")
        unique_together = ("source_product", "target_product", "association_type")
        indexes = [
            models.Index(fields=["source_product", "association_type", "-strength"]),
        ]


class UserProductView(models.Model):
    """
    Model to track user product views for personalized recommendations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="product_views"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="user_views"
    )
    view_count = models.PositiveIntegerField(default=1)
    last_viewed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("user product view")
        verbose_name_plural = _("user product views")
        unique_together = ("user", "product")
        indexes = [
            models.Index(fields=["user", "-last_viewed"]),
            models.Index(fields=["product", "-view_count"]),
        ]

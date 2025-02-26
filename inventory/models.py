from django.db import models

# Create your models here.
# 4. Inventory Management System
# apps/inventory/models.py
from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class Warehouse(models.Model):
    """
    Model for warehouses/locations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Coordinates for mapping and distance calculations
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("warehouse")
        verbose_name_plural = _("warehouses")

    def __str__(self):
        return f"{self.name} ({self.code})"


class InventoryItem(models.Model):
    """
    Model for inventory items at specific warehouses.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="inventory_items"
    )
    product_variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.CASCADE,
        related_name="inventory_items",
        blank=True,
        null=True,
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="inventory_items"
    )

    # Current inventory levels
    quantity_on_hand = models.PositiveIntegerField(default=0)
    quantity_allocated = models.PositiveIntegerField(
        default=0
    )  # Allocated to orders but not shipped
    quantity_available = models.PositiveIntegerField(default=0)  # Calculated field

    # Inventory settings
    reorder_point = models.PositiveIntegerField(default=5)
    reorder_quantity = models.PositiveIntegerField(default=10)
    max_stock_level = models.PositiveIntegerField(default=100)

    # Inventory status
    is_tracking_enabled = models.BooleanField(default=True)
    is_backordering_enabled = models.BooleanField(default=False)

    # Location within warehouse
    bin_location = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_counted = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _("inventory item")
        verbose_name_plural = _("inventory items")
        unique_together = ("product", "product_variant", "warehouse")

    def __str__(self):
        product_name = self.product.name
        if self.product_variant:
            product_name += f" - {self.product_variant.name}"
        return f"{product_name} @ {self.warehouse.name}"

    def save(self, *args, **kwargs):
        """
        Calculate available quantity before saving.
        """
        self.quantity_available = max(
            0, self.quantity_on_hand - self.quantity_allocated
        )
        super().save(*args, **kwargs)

        # Update product's stock quantity
        self._update_product_stock()

    def _update_product_stock(self):
        """
        Update the stock quantity on the product model.
        """
        if self.product_variant:
            # Update variant stock
            total_available = (
                InventoryItem.objects.filter(
                    product_variant=self.product_variant
                ).aggregate(total=Sum("quantity_available"))["total"]
                or 0
            )

            self.product_variant.stock_quantity = total_available
            self.product_variant.save(update_fields=["stock_quantity"])

        # Update product stock
        total_available = (
            InventoryItem.objects.filter(
                product=self.product, product_variant__isnull=True
            ).aggregate(total=Sum("quantity_available"))["total"]
            or 0
        )

        # Add variant stock to product total
        variant_stock = (
            InventoryItem.objects.filter(
                product=self.product, product_variant__isnull=False
            ).aggregate(total=Sum("quantity_available"))["total"]
            or 0
        )

        self.product.stock_quantity = total_available + variant_stock
        self.product.save(update_fields=["stock_quantity"])


class InventoryTransaction(models.Model):
    """
    Model for inventory transactions (adjustments, receiving, fulfillment).
    """

    TRANSACTION_TYPES = [
        ("receipt", "Goods Receipt"),
        ("adjustment", "Inventory Adjustment"),
        ("transfer", "Warehouse Transfer"),
        ("allocation", "Order Allocation"),
        ("fulfillment", "Order Fulfillment"),
        ("return", "Customer Return"),
        ("count", "Physical Count"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)

    # Quantity changes
    quantity = models.IntegerField()  # Can be positive or negative

    # Reference documents
    reference_id = models.UUIDField(blank=True, null=True)  # Order ID, PO ID, etc.
    reference_type = models.CharField(
        max_length=50, blank=True, null=True
    )  # Order, PO, etc.

    # User who performed the transaction
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="inventory_transactions",
    )

    # Notes and metadata
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("inventory transaction")
        verbose_name_plural = _("inventory transactions")
        indexes = [
            models.Index(fields=["inventory_item", "transaction_type"]),
            models.Index(fields=["reference_id", "reference_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.inventory_item} ({self.quantity})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Update inventory quantities if this is a new transaction
        if is_new:
            self._update_inventory_quantities()

    def _update_inventory_quantities(self):
        """
        Update inventory quantities based on the transaction type.
        """
        item = self.inventory_item

        if self.transaction_type in ["receipt", "return", "count"]:
            # Directly add to on-hand quantity
            item.quantity_on_hand += self.quantity
        elif self.transaction_type == "adjustment":
            # Directly adjust on-hand quantity (can be positive or negative)
            item.quantity_on_hand += self.quantity
        elif self.transaction_type == "allocation":
            # Increase allocated quantity
            item.quantity_allocated += self.quantity
        elif self.transaction_type == "fulfillment":
            # Decrease on-hand and allocated quantities
            item.quantity_on_hand -= self.quantity
            item.quantity_allocated -= self.quantity
        elif self.transaction_type == "transfer":
            # For transfers, there should be a corresponding receipt at another warehouse
            item.quantity_on_hand -= self.quantity

        # Ensure quantities don't go negative
        item.quantity_on_hand = max(0, item.quantity_on_hand)
        item.quantity_allocated = max(0, item.quantity_allocated)

        # Save the inventory item
        item.save()

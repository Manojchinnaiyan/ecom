# apps/products/api/serializers.py
from rest_framework import serializers
from apps.products.models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
    ProductReview,
    Inventory,
)


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for product categories.
    """

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "image",
            "order",
            "is_active",
            "children",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_children(self, obj):
        """
        Get child categories.
        """
        children = Category.objects.filter(parent=obj)
        serializer = CategorySimpleSerializer(children, many=True)
        return serializer.data


class CategorySimpleSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for nested category references.
    """

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product images.
    """

    class Meta:
        model = ProductImage
        fields = ["id", "product", "image", "alt_text", "is_primary", "order"]
        read_only_fields = ["id"]


class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Serializer for product variants.
    """

    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "product",
            "name",
            "sku",
            "price_adjustment",
            "stock_quantity",
            "attributes",
            "price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "price"]


class ProductReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for product reviews.
    """

    user_email = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "product",
            "user",
            "user_email",
            "rating",
            "title",
            "content",
            "is_verified_purchase",
            "is_approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "is_verified_purchase",
            "is_approved",
            "created_at",
            "updated_at",
        ]

    def get_user_email(self, obj):
        """
        Get user email (for displaying).
        """
        return obj.user.email if obj.user else None

    def create(self, validated_data):
        """
        Create review with current user.
        """
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class InventorySerializer(serializers.ModelSerializer):
    """
    Serializer for product inventory.
    """

    class Meta:
        model = Inventory
        fields = [
            "id",
            "product",
            "warehouse",
            "reorder_level",
            "reorder_quantity",
            "last_checked",
            "needs_reordering",
        ]
        read_only_fields = ["id", "needs_reordering"]


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for products.
    """

    categories = CategorySimpleSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    inventory = InventorySerializer(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "description",
            "price",
            "compare_at_price",
            "cost_price",
            "categories",
            "stock_quantity",
            "backorder_allowed",
            "max_per_order",
            "is_active",
            "is_featured",
            "is_digital",
            "meta_title",
            "meta_description",
            "images",
            "variants",
            "reviews",
            "inventory",
            "in_stock",
            "is_on_sale",
            "average_rating",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "in_stock",
            "is_on_sale",
            "average_rating",
        ]

    def get_reviews(self, obj):
        """
        Get approved reviews.
        """
        reviews = obj.reviews.filter(is_approved=True)
        serializer = ProductReviewSerializer(reviews, many=True)
        return serializer.data

    def get_average_rating(self, obj):
        """
        Calculate average rating from approved reviews.
        """
        reviews = obj.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 1)
        return None


class ProductListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for product listings.
    """

    primary_image = serializers.SerializerMethodField()
    categories = CategorySimpleSerializer(many=True, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "compare_at_price",
            "primary_image",
            "categories",
            "in_stock",
            "is_on_sale",
            "is_featured",
            "stock_quantity",
        ]
        read_only_fields = ["id", "in_stock", "is_on_sale"]

    def get_primary_image(self, obj):
        """
        Get primary product image URL.
        """
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return self.context["request"].build_absolute_uri(primary.image.url)

        # If no primary image, get the first image
        first_image = obj.images.first()
        if first_image:
            return self.context["request"].build_absolute_uri(first_image.image.url)

        return None

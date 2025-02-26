# apps/recommendations/api/serializers.py
from rest_framework import serializers
from apps.recommendations.models import ProductAssociation
from apps.products.api.serializers import ProductListSerializer


class ProductAssociationSerializer(serializers.ModelSerializer):
    """
    Serializer for product associations.
    """

    target_product = ProductListSerializer(read_only=True)

    class Meta:
        model = ProductAssociation
        fields = [
            "id",
            "source_product",
            "target_product",
            "association_type",
            "strength",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

# apps/recommendations/api/views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.recommendations.models import ProductAssociation
from apps.recommendations.services import RecommendationService
from apps.products.models import Product
from .serializers import ProductAssociationSerializer
from apps.products.api.serializers import ProductListSerializer
from utils.permissions import IsOwnerOrAdmin


class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for product recommendations.
    """

    queryset = ProductAssociation.objects.all()
    serializer_class = ProductAssociationSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def for_product(self, request):
        """
        Get recommendations for a specific product.
        """
        product_id = request.query_params.get("product_id")
        recommendation_type = request.query_params.get("type", "bought_together")
        limit = int(request.query_params.get("limit", 5))

        try:
            product = Product.objects.get(id=product_id)
            recommendations = RecommendationService.get_product_recommendations(
                product, recommendation_type, limit
            )

            serializer = ProductListSerializer(
                recommendations, many=True, context={"request": request}
            )
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def personalized(self, request):
        """
        Get personalized recommendations for the current user.
        """
        limit = int(request.query_params.get("limit", 10))

        recommendations = RecommendationService.get_personalized_recommendations(
            request.user, limit
        )

        serializer = ProductListSerializer(
            recommendations, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def record_view(self, request):
        """
        Record a product view for recommendations.
        """
        product_id = request.data.get("product_id")

        try:
            product = Product.objects.get(id=product_id)
            RecommendationService.record_product_view(request.user, product)
            return Response({"status": "success"})
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)

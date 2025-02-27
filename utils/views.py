# Create a viewset for the global search
# utils/views.py
from rest_framework import views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .search import GlobalSearch
from apps.products.api.serializers import ProductListSerializer
from apps.products.api.serializers import CategorySerializer
from apps.orders.api.serializers import OrderSerializer
from apps.accounts.api.serializers import UserSerializer


class GlobalSearchView(views.APIView):
    """
    Global search endpoint that searches across multiple models.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "")
        results = GlobalSearch.search(query, request.user)

        # Serialize the results
        serialized_results = {}

        if "products" in results:
            serialized_results["products"] = ProductListSerializer(
                results["products"], many=True, context={"request": request}
            ).data

        if "categories" in results:
            serialized_results["categories"] = CategorySerializer(
                results["categories"], many=True
            ).data

        if "orders" in results:
            serialized_results["orders"] = OrderSerializer(
                results["orders"], many=True
            ).data

        if "users" in results and request.user.is_staff:
            serialized_results["users"] = UserSerializer(
                results["users"], many=True
            ).data

        return Response(serialized_results)

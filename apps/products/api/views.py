# apps/products/api/views.py
from django.db.models import Q, Count, Avg
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.products.models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
    ProductReview,
    Inventory,
)
from .serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductImageSerializer,
    ProductVariantSerializer,
    ProductReviewSerializer,
    InventorySerializer,
)
from utils.permissions import IsOwnerOrAdmin, ReadOnly


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for product categories.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "order"]
    lookup_field = "slug"

    def get_permissions(self):
        """
        Allow read access to anyone, restrict write to staff.
        """
        if self.action in ["list", "retrieve"]:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=["get"])
    def products(self, request, slug=None):
        """
        Get all products in a category.
        """
        category = self.get_object()
        products = Product.objects.filter(
            Q(categories=category) | Q(categories__parent=category)
        ).distinct()

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(
            products, many=True, context={"request": request}
        )
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint for products.
    """

    queryset = Product.objects.all()
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["categories", "is_active", "is_featured", "is_digital", "price"]
    search_fields = ["name", "description", "sku"]
    ordering_fields = ["name", "price", "created_at", "stock_quantity"]
    lookup_field = "slug"

    def get_serializer_class(self):
        """
        Return different serializers for list and detail views.
        """
        if self.action == "list":
            return ProductListSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        """
        Allow read access to anyone, restrict write to staff.
        """
        if self.action in ["list", "retrieve", "reviews"]:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """
        Get featured products.
        """
        featured = Product.objects.filter(is_featured=True, is_active=True)
        page = self.paginate_queryset(featured)

        if page is not None:
            serializer = ProductListSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(
            featured, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def on_sale(self, request):
        """
        Get products on sale.
        """
        on_sale = (
            Product.objects.filter(is_active=True)
            .exclude(compare_at_price__isnull=True)
            .exclude(compare_at_price=0)
        )

        page = self.paginate_queryset(on_sale)
        if page is not None:
            serializer = ProductListSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(
            on_sale, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def reviews(self, request, slug=None):
        """
        Get approved reviews for a product.
        """
        product = self.get_object()
        reviews = product.reviews.filter(is_approved=True)

        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ProductReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def add_review(self, request, slug=None):
        """
        Add a review for a product.
        """
        product = self.get_object()

        # Check if user already reviewed this product
        if ProductReview.objects.filter(product=product, user=request.user).exists():
            return Response(
                {"detail": "You have already reviewed this product."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProductReviewSerializer(
            data={**request.data, "product": product.id}, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def search_suggestions(self, request):
        """
        Get search suggestions based on partial input.
        """
        query = request.query_params.get("q", "")
        if not query or len(query) < 2:
            return Response([])

        # Get matching products
        products = Product.objects.filter(name__icontains=query)[:5].values_list(
            "name", flat=True
        )

        # Get matching categories
        categories = Category.objects.filter(name__icontains=query)[:3].values_list(
            "name", flat=True
        )

        # Combine and format results
        suggestions = list(products) + [f"Category: {cat}" for cat in categories]

        return Response(suggestions)


class ProductImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for product images.
    """

    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "is_primary"]
    ordering_fields = ["order"]


class ProductVariantViewSet(viewsets.ModelViewSet):
    """
    API endpoint for product variants.
    """

    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["product"]
    search_fields = ["name", "sku"]


class ProductReviewViewSet(viewsets.ModelViewSet):
    """
    API endpoint for product reviews.
    """

    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "user", "rating", "is_approved"]
    ordering_fields = ["created_at", "rating"]

    def get_permissions(self):
        """
        Allow users to create reviews but only admins can list all.
        """
        if self.action == "create":
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [IsOwnerOrAdmin]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class InventoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for product inventory.
    """

    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product", "warehouse", "needs_reordering"]

# apps/orders/api/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import F, Sum

from apps.orders.models import Order, OrderItem, Cart, CartItem, Coupon
from .serializers import (
    OrderSerializer,
    OrderItemSerializer,
    CartSerializer,
    CartItemSerializer,
    CouponSerializer,
    CouponValidateSerializer,
    OrderCreateSerializer,
)
from utils.permissions import IsOwnerOrAdmin


class OrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint for orders.
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "updated_at", "total"]

    def get_queryset(self):
        """
        Return orders for the current user or all orders for staff.
        """
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """
        Return different serializers for list and create actions.
        """
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cancel an order.
        """
        order = self.get_object()

        # Check if order can be cancelled
        if order.status not in ["pending", "processing"]:
            return Response(
                {"detail": "Order cannot be cancelled in its current state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update order status
        order.update_status("cancelled", "Cancelled by customer")

        return Response({"detail": "Order cancelled successfully."})


class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for order items (read-only).
    """

    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["order", "product"]

    def get_queryset(self):
        """
        Return order items for the current user's orders.
        """
        if self.request.user.is_staff:
            return OrderItem.objects.all()
        return OrderItem.objects.filter(order__user=self.request.user)


class CartViewSet(viewsets.ModelViewSet):
    """
    API endpoint for shopping carts.
    """

    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Return cart for the current user.
        """
        if self.request.user.is_staff:
            return Cart.objects.all()
        return Cart.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """
        Get the current user's cart or create one if it doesn't exist.
        """
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            cart = Cart.objects.create(user=request.user)

        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def apply_coupon(self, request, pk=None):
        """
        Apply a coupon to the cart.
        """
        cart = self.get_object()
        code = request.data.get("code")

        if not code:
            return Response(
                {"detail": "Coupon code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate coupon
        try:
            coupon = Coupon.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now(),
            )

            # Check usage limit
            if coupon.usage_limit > 0 and coupon.used_count >= coupon.usage_limit:
                return Response(
                    {"detail": "This coupon has reached its usage limit."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check minimum order amount
            cart_subtotal = cart.subtotal
            if cart_subtotal < coupon.minimum_order_amount:
                return Response(
                    {
                        "detail": f"This coupon requires a minimum order amount of ${coupon.minimum_order_amount}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Apply coupon
            cart.coupon_code = code
            cart.save()

            return Response({"detail": "Coupon applied successfully."})

        except Coupon.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired coupon code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def remove_coupon(self, request, pk=None):
        """
        Remove a coupon from the cart.
        """
        cart = self.get_object()
        cart.coupon_code = None
        cart.save()

        return Response({"detail": "Coupon removed successfully."})

    @action(detail=True, methods=["post"])
    def clear(self, request, pk=None):
        """
        Clear all items from the cart.
        """
        cart = self.get_object()
        cart.items.all().delete()

        return Response({"detail": "Cart cleared successfully."})


class CartItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint for cart items.
    """

    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Return cart items for the current user's cart.
        """
        if self.request.user.is_staff:
            return CartItem.objects.all()
        return CartItem.objects.filter(cart__user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Add item to cart.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def update(self, request, *args, **kwargs):
        """
        Update cart item quantity.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def perform_create(self, serializer):
        """
        Save cart item with current user's cart.
        """
        user = self.request.user

        # Get or create cart for user
        cart, created = Cart.objects.get_or_create(user=user)

        serializer.save(cart=cart)


class CouponViewSet(viewsets.ModelViewSet):
    """
    API endpoint for coupons.
    """

    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active", "discount_type"]
    search_fields = ["code", "description"]

    def get_permissions(self):
        """
        Allow validation for all, restrict other operations to staff.
        """
        if self.action == "validate":
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["post"])
    def validate(self, request):
        """
        Validate a coupon code.
        """
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        cart_id = serializer.validated_data.get("cart_id")

        try:
            coupon = Coupon.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now(),
            )

            # Check usage limit
            if coupon.usage_limit > 0 and coupon.used_count >= coupon.usage_limit:
                return Response(
                    {
                        "valid": False,
                        "detail": "This coupon has reached its usage limit.",
                    }
                )

            # If cart_id provided, validate minimum order amount
            if cart_id:
                try:
                    cart = Cart.objects.get(id=cart_id, user=request.user)
                    cart_subtotal = cart.subtotal

                    if cart_subtotal < coupon.minimum_order_amount:
                        return Response(
                            {
                                "valid": False,
                                "detail": f"This coupon requires a minimum order amount of ${coupon.minimum_order_amount}.",
                            }
                        )
                except Cart.DoesNotExist:
                    pass

            # Calculate discount
            discount_info = {
                "type": coupon.discount_type,
                "value": float(coupon.discount_value),
            }

            return Response(
                {
                    "valid": True,
                    "discount": discount_info,
                    "minimum_order_amount": float(coupon.minimum_order_amount),
                }
            )

        except Coupon.DoesNotExist:
            return Response(
                {"valid": False, "detail": "Invalid or expired coupon code."}
            )

# apps/orders/api/serializers.py
from rest_framework import serializers
from apps.orders.models import Order, OrderItem, Cart, CartItem, Coupon
from apps.products.api.serializers import ProductListSerializer
from apps.accounts.api.serializers import AddressSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for order items.
    """

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "product",
            "product_variant",
            "product_name",
            "variant_name",
            "sku",
            "price",
            "quantity",
            "discount_amount",
            "tax_amount",
            "subtotal",
            "total",
            "options",
            "is_digital",
        ]
        read_only_fields = ["id", "subtotal", "total"]


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for orders.
    """

    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    billing_address = AddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "user",
            "status",
            "created_at",
            "updated_at",
            "shipping_address",
            "billing_address",
            "subtotal",
            "shipping_cost",
            "tax_amount",
            "discount_amount",
            "total",
            "shipping_method",
            "tracking_number",
            "notes",
            "items",
            "coupon_code",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "created_at",
            "updated_at",
            "user",
            "subtotal",
            "total",
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating orders.
    """

    shipping_address_id = serializers.UUIDField(write_only=True)
    billing_address_id = serializers.UUIDField(write_only=True)
    cart_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = [
            "shipping_address_id",
            "billing_address_id",
            "shipping_method",
            "notes",
            "cart_id",
            "coupon_code",
        ]

    def validate(self, attrs):
        """
        Validate the shipping and billing addresses belong to the user.
        """
        user = self.context["request"].user

        # Validate shipping address
        shipping_address_id = attrs.get("shipping_address_id")
        from apps.accounts.models import Address

        try:
            shipping_address = Address.objects.get(id=shipping_address_id, user=user)
            attrs["shipping_address"] = shipping_address
        except Address.DoesNotExist:
            raise serializers.ValidationError(
                {"shipping_address_id": "Invalid shipping address"}
            )

        # Validate billing address
        billing_address_id = attrs.get("billing_address_id")
        try:
            billing_address = Address.objects.get(id=billing_address_id, user=user)
            attrs["billing_address"] = billing_address
        except Address.DoesNotExist:
            raise serializers.ValidationError(
                {"billing_address_id": "Invalid billing address"}
            )

        # Validate cart if provided
        cart_id = attrs.get("cart_id")
        if cart_id:
            try:
                cart = Cart.objects.get(id=cart_id, user=user)

                # Check if cart has items
                if cart.items.count() == 0:
                    raise serializers.ValidationError({"cart_id": "Cart is empty"})

                attrs["cart"] = cart
            except Cart.DoesNotExist:
                raise serializers.ValidationError({"cart_id": "Invalid cart"})

        return attrs

    def create(self, validated_data):
        """
        Create an order from cart and addresses.
        """
        user = self.context["request"].user
        shipping_address = validated_data.pop("shipping_address")
        billing_address = validated_data.pop("billing_address")
        cart = validated_data.pop("cart", None)
        coupon_code = validated_data.pop("coupon_code", None)

        # Initialize order totals
        subtotal = 0
        tax_amount = 0
        discount_amount = 0

        # Create the order
        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            billing_address=billing_address,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total=subtotal + tax_amount - discount_amount,
            coupon_code=coupon_code,
            **validated_data
        )

        # If cart provided, copy items to order
        if cart:
            for cart_item in cart.items.all():
                product = cart_item.product
                variant = cart_item.product_variant

                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_variant=variant,
                    product_name=product.name,
                    variant_name=variant.name if variant else None,
                    sku=variant.sku if variant else product.sku,
                    price=variant.price if variant else product.price,
                    quantity=cart_item.quantity,
                    is_digital=product.is_digital,
                )

                # Update order subtotal
                subtotal += (
                    variant.price if variant else product.price
                ) * cart_item.quantity

            # Apply coupon if provided
            if coupon_code:
                from django.utils import timezone

                try:
                    coupon = Coupon.objects.get(
                        code=coupon_code,
                        is_active=True,
                        valid_from__lte=timezone.now(),
                        valid_to__gte=timezone.now(),
                    )

                    if subtotal >= coupon.minimum_order_amount:
                        if coupon.discount_type == "percentage":
                            discount_amount = subtotal * (coupon.discount_value / 100)
                        elif coupon.discount_type == "fixed":
                            discount_amount = min(coupon.discount_value, subtotal)

                        # Update coupon usage
                        coupon.used_count += 1
                        coupon.save()
                except Coupon.DoesNotExist:
                    pass

            # Calculate tax (simplified - in real world this would use tax service)
            tax_amount = subtotal * 0.1  # 10% tax rate example

            # Update order totals
            order.subtotal = subtotal
            order.tax_amount = tax_amount
            order.discount_amount = discount_amount
            order.total = subtotal + tax_amount - discount_amount
            order.save()

            # Clear the cart after creating order
            cart.delete()

        return order


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for cart items.
    """

    product_details = ProductListSerializer(source="product", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "cart",
            "product",
            "product_variant",
            "quantity",
            "product_details",
            "subtotal",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "cart", "created_at", "updated_at", "subtotal"]

    def create(self, validated_data):
        """
        Add item to cart, updating quantity if product already exists.
        """
        request = self.context.get("request")
        user = request.user if request and hasattr(request, "user") else None

        product = validated_data.get("product")
        product_variant = validated_data.get("product_variant")
        quantity = validated_data.get("quantity", 1)

        # Get or create cart for user
        from apps.orders.models import Cart

        cart, created = Cart.objects.get_or_create(user=user, defaults={"user": user})

        # Check if product already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            product_variant=product_variant,
            defaults={
                "cart": cart,
                "product": product,
                "product_variant": product_variant,
                "quantity": quantity,
            },
        )

        if not created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for shopping cart.
    """

    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
            "items",
            "subtotal",
            "item_count",
            "coupon_code",
        ]
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
            "subtotal",
            "item_count",
        ]


class CouponSerializer(serializers.ModelSerializer):
    """
    Serializer for coupons.
    """

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "valid_from",
            "valid_to",
            "is_active",
            "usage_limit",
            "used_count",
            "minimum_order_amount",
            "apply_to_products",
            "apply_to_categories",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "used_count", "created_at"]


class CouponValidateSerializer(serializers.Serializer):
    """
    Serializer for validating coupons.
    """

    code = serializers.CharField(required=True)
    cart_id = serializers.UUIDField(required=False)

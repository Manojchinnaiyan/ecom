# apps/payments/api/serializers.py
from rest_framework import serializers
from apps.payments.models import Payment, Refund, PaymentMethod, Invoice, Transaction
from apps.orders.api.serializers import OrderSerializer


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for payments.
    """

    order_details = OrderSerializer(source="order", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "payment_method",
            "amount",
            "currency",
            "status",
            "transaction_id",
            "payment_gateway",
            "gateway_response",
            "created_at",
            "updated_at",
            "order_details",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "order_details"]


class PaymentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating payments.
    """

    order_id = serializers.UUIDField()
    payment_method_id = serializers.UUIDField(required=False)

    class Meta:
        model = Payment
        fields = [
            "order_id",
            "payment_method",
            "payment_method_id",
            "amount",
            "currency",
            "payment_gateway",
        ]

    def validate(self, attrs):
        """
        Validate the order belongs to the user and is in a valid state.
        """
        user = self.context["request"].user
        order_id = attrs.pop("order_id")

        # Validate order
        from apps.orders.models import Order

        try:
            order = Order.objects.get(id=order_id, user=user)

            # Check if order is in a valid state for payment
            if order.status not in ["pending", "processing"]:
                raise serializers.ValidationError(
                    {"order_id": "Order is not in a valid state for payment"}
                )

            attrs["order"] = order
        except Order.DoesNotExist:
            raise serializers.ValidationError({"order_id": "Invalid order"})

        # Validate payment method if provided
        payment_method_id = attrs.pop("payment_method_id", None)
        if payment_method_id:
            try:
                payment_method = PaymentMethod.objects.get(
                    id=payment_method_id, user=user
                )
                attrs["payment_method"] = payment_method.payment_type
                attrs["payment_gateway"] = f"{payment_method.payment_type}_gateway"
            except PaymentMethod.DoesNotExist:
                raise serializers.ValidationError(
                    {"payment_method_id": "Invalid payment method"}
                )

        # Set default amount if not provided
        if "amount" not in attrs:
            attrs["amount"] = order.total

        return attrs

    def create(self, validated_data):
        """
        Process payment through payment gateway.
        """
        order = validated_data.get("order")
        payment_method = validated_data.get("payment_method")
        amount = validated_data.get("amount")

        # Simulate payment gateway processing
        # In a real application, you would integrate with a payment provider API
        import uuid

        gateway_response = {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
            "timestamp": "2023-01-01T12:00:00Z",
            "amount": float(amount),
            "currency": validated_data.get("currency", "USD"),
        }

        # Create payment record
        payment = Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=amount,
            currency=validated_data.get("currency", "USD"),
            status="completed",
            transaction_id=gateway_response["transaction_id"],
            payment_gateway=validated_data.get("payment_gateway", "default_gateway"),
            gateway_response=gateway_response,
        )

        # Update order status
        order.update_status("processing", "Payment received")

        # Create transaction record
        Transaction.objects.create(
            user=order.user,
            order=order,
            payment=payment,
            transaction_type="payment",
            amount=amount,
            currency=validated_data.get("currency", "USD"),
            description=f"Payment for order {order.order_number}",
            external_id=gateway_response["transaction_id"],
            gateway=validated_data.get("payment_gateway", "default_gateway"),
            gateway_response=gateway_response,
        )

        return payment


class RefundSerializer(serializers.ModelSerializer):
    """
    Serializer for refunds.
    """

    class Meta:
        model = Refund
        fields = [
            "id",
            "order",
            "payment",
            "amount",
            "status",
            "reason",
            "notes",
            "transaction_id",
            "gateway_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RefundCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating refunds.
    """

    order_id = serializers.UUIDField()
    payment_id = serializers.UUIDField()

    class Meta:
        model = Refund
        fields = ["order_id", "payment_id", "amount", "reason", "notes"]

    def validate(self, attrs):
        """
        Validate the order and payment belong to the user and are in valid states.
        """
        user = self.context["request"].user
        order_id = attrs.pop("order_id")
        payment_id = attrs.pop("payment_id")

        # Validate order
        from apps.orders.models import Order

        try:
            order = Order.objects.get(id=order_id)

            # Check if user is authorized
            if not user.is_staff and order.user != user:
                raise serializers.ValidationError(
                    {
                        "order_id": "You are not authorized to request a refund for this order"
                    }
                )

            # Check if order is in a valid state for refund
            if order.status not in ["processing", "shipped", "delivered"]:
                raise serializers.ValidationError(
                    {"order_id": "Order is not in a valid state for refund"}
                )

            attrs["order"] = order
        except Order.DoesNotExist:
            raise serializers.ValidationError({"order_id": "Invalid order"})

        # Validate payment
        try:
            payment = Payment.objects.get(id=payment_id, order=order)

            # Check if payment is completed
            if payment.status != "completed":
                raise serializers.ValidationError(
                    {"payment_id": "Payment is not in a completed state"}
                )

            # Check if amount is valid
            refund_amount = attrs.get("amount")
            if refund_amount > payment.amount:
                raise serializers.ValidationError(
                    {"amount": "Refund amount cannot exceed the payment amount"}
                )

            attrs["payment"] = payment
        except Payment.DoesNotExist:
            raise serializers.ValidationError({"payment_id": "Invalid payment"})

        return attrs

    def create(self, validated_data):
        """
        Process refund through payment gateway.
        """
        order = validated_data.get("order")
        payment = validated_data.get("payment")
        amount = validated_data.get("amount")
        reason = validated_data.get("reason")

        # Simulate refund processing
        # In a real application, you would integrate with a payment provider API
        import uuid

        gateway_response = {
            "success": True,
            "refund_id": str(uuid.uuid4()),
            "original_transaction_id": payment.transaction_id,
            "timestamp": "2023-01-01T12:00:00Z",
            "amount": float(amount),
            "currency": payment.currency,
        }

        # Create refund record
        refund = Refund.objects.create(
            order=order,
            payment=payment,
            amount=amount,
            status="completed",
            reason=reason,
            notes=validated_data.get("notes"),
            transaction_id=gateway_response["refund_id"],
            gateway_response=gateway_response,
        )

        # Update order status if full refund
        if amount >= payment.amount:
            order.update_status("refunded", f"Full refund processed: {reason}")
        else:
            order.update_status(
                "partially_refunded", f"Partial refund processed: {reason}"
            )

        # Create transaction record
        Transaction.objects.create(
            user=order.user,
            order=order,
            refund=refund,
            transaction_type="refund",
            amount=amount,
            currency=payment.currency,
            description=f"Refund for order {order.order_number}: {reason}",
            external_id=gateway_response["refund_id"],
            gateway=payment.payment_gateway,
            gateway_response=gateway_response,
        )

        return refund


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializer for payment methods.
    """

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "user",
            "payment_type",
            "is_default",
            "card_last4",
            "card_expiry_month",
            "card_expiry_year",
            "card_brand",
            "gateway_token",
            "billing_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def create(self, validated_data):
        """
        Create a payment method with the current user.
        """
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for invoices.
    """

    class Meta:
        model = Invoice
        fields = [
            "id",
            "order",
            "invoice_number",
            "status",
            "due_date",
            "tax_id",
            "notes",
            "invoice_pdf",
            "created_at",
            "updated_at",
            "sent_at",
            "paid_at",
        ]
        read_only_fields = [
            "id",
            "invoice_number",
            "created_at",
            "updated_at",
            "sent_at",
            "paid_at",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for transactions.
    """

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user",
            "order",
            "payment",
            "refund",
            "transaction_type",
            "amount",
            "currency",
            "description",
            "external_id",
            "gateway",
            "gateway_response",
            "created_at",
            "ip_address",
        ]
        read_only_fields = ["id", "created_at", "ip_address"]

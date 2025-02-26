# apps/analytics/services.py
from django.db.models import Sum, Count, Avg, F, Q, ExpressionWrapper, FloatField
from django.db.models.functions import (
    TruncDate,
    TruncWeek,
    TruncMonth,
    TruncQuarter,
    TruncYear,
)
from apps.analytics.models import ProductPerformance, SalesByPeriod
from apps.orders.models import Order, OrderItem
from apps.products.models import Product, ProductReview
from apps.recommendations.models import UserProductView
from datetime import datetime, timedelta
import pandas as pd


class AnalyticsService:
    """
    Service class for analytics and reporting.
    """

    @staticmethod
    def update_product_performance(start_date=None, end_date=None):
        """
        Update product performance metrics.
        """
        if not start_date:
            # Default to last 30 days
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)

        products = Product.objects.all()

        for product in products:
            # Get order items for this product in the date range
            order_items = OrderItem.objects.filter(
                product=product,
                order__created_at__date__gte=start_date,
                order__created_at__date__lte=end_date,
            )

            # Calculate sales metrics
            total_sales = order_items.count()
            total_revenue = (
                order_items.aggregate(total=Sum(F("price") * F("quantity")))["total"]
                or 0
            )

            # Get unique customers who purchased this product
            unique_customers = order_items.values("order__user").distinct().count()

            # Get product views
            views = (
                UserProductView.objects.filter(
                    product=product,
                    last_viewed__date__gte=start_date,
                    last_viewed__date__lte=end_date,
                ).aggregate(total_views=Sum("view_count"))["total_views"]
                or 0
            )

            # Calculate conversion rate
            conversion_rate = 0
            if views > 0:
                conversion_rate = (total_sales / views) * 100

            # Get review metrics
            reviews = ProductReview.objects.filter(
                product=product,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            review_count = reviews.count()
            average_rating = reviews.aggregate(avg=Avg("rating"))["avg"] or 0

            # Calculate repeat purchase rate
            # Count customers who bought this product more than once
            repeat_customers = (
                Order.objects.filter(
                    items__product=product,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                )
                .values("user")
                .annotate(order_count=Count("id"))
                .filter(order_count__gt=1)
                .count()
            )

            repeat_purchase_rate = 0
            if unique_customers > 0:
                repeat_purchase_rate = (repeat_customers / unique_customers) * 100

            # Calculate average order value
            average_order_value = 0
            if total_sales > 0:
                average_order_value = total_revenue / total_sales

            # Update or create performance record
            ProductPerformance.objects.update_or_create(
                product=product,
                start_date=start_date,
                end_date=end_date,
                defaults={
                    "total_sales": total_sales,
                    "total_revenue": total_revenue,
                    "average_order_value": average_order_value,
                    "views": views,
                    "conversions": total_sales,
                    "conversion_rate": conversion_rate,
                    "unique_customers": unique_customers,
                    "repeat_purchase_rate": repeat_purchase_rate,
                    "review_count": review_count,
                    "average_rating": average_rating,
                },
            )

    @staticmethod
    def update_sales_by_period(period_type="monthly", start_date=None, end_date=None):
        """
        Update sales aggregates by period.
        """
        if not end_date:
            end_date = datetime.now().date()

        if not start_date:
            # Set appropriate default based on period type
            if period_type == "daily":
                start_date = end_date - timedelta(days=30)  # Last 30 days
            elif period_type == "weekly":
                start_date = end_date - timedelta(weeks=12)  # Last 12 weeks
            elif period_type == "monthly":
                start_date = end_date - timedelta(days=365)  # Last 12 months
            elif period_type == "quarterly":
                start_date = end_date - timedelta(days=730)  # Last 2 years
            else:  # yearly
                start_date = end_date - timedelta(days=1825)  # Last 5 years

        # Get all orders in the date range
        orders = Order.objects.filter(
            created_at__date__gte=start_date, created_at__date__lte=end_date
        )

        # Get the appropriate truncation function
        if period_type == "daily":
            trunc_func = TruncDate("created_at")
        elif period_type == "weekly":
            trunc_func = TruncWeek("created_at")
        elif period_type == "monthly":
            trunc_func = TruncMonth("created_at")
        elif period_type == "quarterly":
            trunc_func = TruncQuarter("created_at")
        else:  # yearly
            trunc_func = TruncYear("created_at")

        # Aggregate orders by period
        order_aggregates = (
            orders.annotate(period=trunc_func)
            .values("period")
            .annotate(
                order_count=Count("id"),
                total_revenue=Sum("total"),
                item_count=Sum(Count("items")),
                discount_amount=Sum("discount_amount"),
                shipping_revenue=Sum("shipping_cost"),
                tax_revenue=Sum("tax_amount"),
            )
            .order_by("period")
        )

        # Prepare data for bulk creation/update
        sales_periods = []

        for agg in order_aggregates:
            period_start = agg["period"]

            # Calculate period end based on period type
            if period_type == "daily":
                period_end = period_start
            elif period_type == "weekly":
                period_end = period_start + timedelta(days=6)
            elif period_type == "monthly":
                # Get last day of month
                if period_start.month == 12:
                    period_end = period_start.replace(day=31)
                else:
                    next_month = period_start.replace(month=period_start.month + 1)
                    period_end = next_month - timedelta(days=1)
            elif period_type == "quarterly":
                # Get last day of quarter
                quarter_end_month = (
                    (period_start.month + 2) if period_start.month <= 10 else 12
                )
                if quarter_end_month == 12:
                    period_end = period_start.replace(month=quarter_end_month, day=31)
                else:
                    next_month = period_start.replace(month=quarter_end_month + 1)
                    period_end = next_month - timedelta(days=1)
            else:  # yearly
                period_end = period_start.replace(month=12, day=31)

            # Calculate new vs returning customers
            customers_in_period = (
                orders.filter(
                    created_at__date__gte=period_start, created_at__date__lte=period_end
                )
                .values("user")
                .distinct()
            )

            # Get customers who had ordered before this period
            prior_customers = (
                Order.objects.filter(created_at__date__lt=period_start)
                .values("user")
                .distinct()
            )

            returning_customers = customers_in_period.filter(
                user__in=prior_customers.values("user")
            ).count()

            new_customers = customers_in_period.count() - returning_customers

            # Update or create sales period record
            sales_period, created = SalesByPeriod.objects.update_or_create(
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                defaults={
                    "order_count": agg["order_count"],
                    "total_revenue": agg["total_revenue"],
                    "item_count": agg["item_count"],
                    "discount_amount": agg["discount_amount"],
                    "shipping_revenue": agg["shipping_revenue"],
                    "tax_revenue": agg["tax_revenue"],
                    "new_customers": new_customers,
                    "returning_customers": returning_customers,
                },
            )

            sales_periods.append(sales_period)

        return sales_periods

    @staticmethod
    def get_sales_report(period_type="monthly", start_date=None, end_date=None):
        """
        Get sales report for the specified period.
        """
        # Ensure we have up-to-date data
        AnalyticsService.update_sales_by_period(period_type, start_date, end_date)

        # Get sales data
        sales_data = SalesByPeriod.objects.filter(
            period_type=period_type,
            period_start__gte=start_date if start_date else datetime(1970, 1, 1),
            period_end__lte=end_date if end_date else datetime.now().date(),
        ).order_by("period_start")

        return sales_data

    @staticmethod
    def get_top_products(limit=10, metric="revenue", start_date=None, end_date=None):
        """
        Get top performing products by the specified metric.
        """
        # Ensure we have up-to-date data
        AnalyticsService.update_product_performance(start_date, end_date)

        # Map metric to field name
        field_map = {
            "revenue": "-total_revenue",
            "sales": "-total_sales",
            "conversion": "-conversion_rate",
            "rating": "-average_rating",
        }

        order_by = field_map.get(metric, "-total_revenue")

        # Get top products
        top_products = ProductPerformance.objects.order_by(order_by)[:limit]

        return top_products

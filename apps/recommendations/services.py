# apps/recommendations/services.py
from collections import defaultdict
from apps.recommendations.models import ProductAssociation, UserProductView
from apps.products.models import Product
from django.db.models import Count, F, Q


class RecommendationService:
    """
    Service class for generating product recommendations.
    """

    @staticmethod
    def get_product_recommendations(
        product, recommendation_type="bought_together", limit=5
    ):
        """
        Get recommended products for a specific product.
        """
        associations = ProductAssociation.objects.filter(
            source_product=product, association_type=recommendation_type
        ).order_by("-strength")[:limit]

        return [assoc.target_product for assoc in associations]

    @staticmethod
    def get_personalized_recommendations(user, limit=10):
        """
        Get personalized product recommendations for a user.
        """
        if not user or not user.is_authenticated:
            # Return popular products for anonymous users
            return Product.objects.filter(is_active=True).order_by("-reviews")[:limit]

        # Get user's recently viewed products
        viewed_products = UserProductView.objects.filter(user=user).order_by(
            "-last_viewed"
        )[:20]

        if not viewed_products:
            # If no view history, return popular products
            return Product.objects.filter(is_active=True).order_by("-reviews")[:limit]

        # Get product IDs viewed by user
        viewed_product_ids = [view.product_id for view in viewed_products]

        # Find similar products based on view patterns
        similar_products = ProductAssociation.objects.filter(
            source_product_id__in=viewed_product_ids, association_type="viewed_together"
        ).order_by("-strength")

        # Get product IDs, avoiding products the user has already viewed
        recommended_product_ids = set()
        for assoc in similar_products:
            if assoc.target_product_id not in viewed_product_ids:
                recommended_product_ids.add(assoc.target_product_id)
                if len(recommended_product_ids) >= limit:
                    break

        # If not enough recommendations, add complementary products
        if len(recommended_product_ids) < limit:
            complementary = ProductAssociation.objects.filter(
                source_product_id__in=viewed_product_ids,
                association_type="complementary",
            ).order_by("-strength")

            for assoc in complementary:
                if (
                    assoc.target_product_id not in viewed_product_ids
                    and assoc.target_product_id not in recommended_product_ids
                ):
                    recommended_product_ids.add(assoc.target_product_id)
                    if len(recommended_product_ids) >= limit:
                        break

        # Return the recommended products
        return Product.objects.filter(id__in=recommended_product_ids, is_active=True)

    @staticmethod
    def record_product_view(user, product):
        """
        Record that a user viewed a product.
        """
        if not user or not user.is_authenticated:
            return

        view, created = UserProductView.objects.get_or_create(
            user=user, product=product, defaults={"view_count": 1}
        )

        if not created:
            view.view_count += 1
            view.save()

    @staticmethod
    def update_product_associations():
        """
        Update product associations based on order history.
        This would typically be run as a scheduled task.
        """
        from apps.orders.models import OrderItem
        from django.db import connection

        # Find products frequently bought together
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.product_id as source_id, b.product_id as target_id, COUNT(*) as frequency
                FROM orders_orderitem a
                JOIN orders_orderitem b ON a.order_id = b.order_id AND a.product_id != b.product_id
                GROUP BY a.product_id, b.product_id
                HAVING COUNT(*) > 1
                ORDER BY frequency DESC
            """
            )

            # Process the results
            bought_together = defaultdict(list)
            for source_id, target_id, frequency in cursor.fetchall():
                bought_together[source_id].append((target_id, frequency))

        # Calculate max frequency for normalization
        max_frequency = 1
        for products in bought_together.values():
            for _, frequency in products:
                max_frequency = max(max_frequency, frequency)

        # Create/update associations
        associations = []
        for source_id, targets in bought_together.items():
            source_product = Product.objects.get(id=source_id)

            for target_id, frequency in targets:
                target_product = Product.objects.get(id=target_id)
                strength = frequency / max_frequency  # Normalize to 0-1

                association, _ = ProductAssociation.objects.update_or_create(
                    source_product=source_product,
                    target_product=target_product,
                    association_type="bought_together",
                    defaults={"strength": strength},
                )
                associations.append(association)

        return len(associations)

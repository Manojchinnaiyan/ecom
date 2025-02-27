# Search implementation for the entire site
# utils/search.py
from django.db.models import Q
from apps.products.models import Product, Category
from apps.accounts.models import User
from apps.orders.models import Order


class GlobalSearch:
    """
    Global search functionality across multiple models.
    """

    @staticmethod
    def search(query, user=None):
        """
        Search across multiple models and return grouped results.

        Args:
            query: The search query string
            user: Optional authenticated user for user-specific results

        Returns:
            Dict of search results grouped by model
        """
        if not query or len(query) < 2:
            return {}

        results = {
            "products": GlobalSearch._search_products(query),
            "categories": GlobalSearch._search_categories(query),
        }

        # Add user-specific searches if user is authenticated
        if user and user.is_authenticated:
            results.update(
                {
                    "orders": GlobalSearch._search_orders(query, user),
                }
            )

            # Add admin-only searches
            if user.is_staff:
                results.update(
                    {
                        "users": GlobalSearch._search_users(query),
                    }
                )

        return results

    @staticmethod
    def _search_products(query):
        """Search for products."""
        return Product.objects.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(sku__icontains=query)
            | Q(meta_title__icontains=query)
            | Q(meta_description__icontains=query)
        ).distinct()[:20]

    @staticmethod
    def _search_categories(query):
        """Search for categories."""
        return Category.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).distinct()[:10]

    @staticmethod
    def _search_orders(query, user):
        """Search for user's orders."""
        return Order.objects.filter(
            Q(user=user),
            Q(order_number__icontains=query) | Q(items__product_name__icontains=query),
        ).distinct()[:10]

    @staticmethod
    def _search_users(query):
        """Search for users (admin only)."""
        return User.objects.filter(
            Q(email__icontains=query)
            | Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone__icontains=query)
        ).distinct()[:20]

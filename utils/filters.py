# utils/filters.py
from django_filters import rest_framework as filters
from django.db.models import Avg, Min, Max, Count
from apps.products.models import Product, Category, ProductReview


class ProductFilter(filters.FilterSet):
    """
    Advanced filter set for products with all enterprise-grade filtering options.
    """

    # Price range filters
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")

    # Rating filters
    min_rating = filters.NumberFilter(method="filter_min_rating")
    max_rating = filters.NumberFilter(method="filter_max_rating")

    # Category filters
    category = filters.ModelMultipleChoiceFilter(
        field_name="categories",
        queryset=Category.objects.all(),
        to_field_name="slug",
    )
    category_tree = filters.CharFilter(method="filter_category_tree")

    # Stock filters
    in_stock = filters.BooleanFilter(method="filter_in_stock")

    # Variant filters
    has_variants = filters.BooleanFilter(method="filter_has_variants")
    variant_attribute = filters.CharFilter(method="filter_variant_attribute")

    # Review filters
    min_reviews = filters.NumberFilter(method="filter_min_reviews")

    # Date filters
    created_after = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.DateFilter(field_name="created_at", lookup_expr="lte")
    updated_after = filters.DateFilter(field_name="updated_at", lookup_expr="gte")
    updated_before = filters.DateFilter(field_name="updated_at", lookup_expr="lte")

    # Boolean filters
    is_featured = filters.BooleanFilter()
    is_on_sale = filters.BooleanFilter(method="filter_is_on_sale")
    is_new = filters.BooleanFilter(method="filter_is_new")

    # Text search
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = Product
        fields = [
            "min_price",
            "max_price",
            "min_rating",
            "max_rating",
            "category",
            "category_tree",
            "in_stock",
            "has_variants",
            "variant_attribute",
            "min_reviews",
            "created_after",
            "created_before",
            "updated_after",
            "updated_before",
            "is_featured",
            "is_on_sale",
            "is_new",
            "search",
        ]

    def filter_min_rating(self, queryset, name, value):
        """Filter products by minimum average rating."""
        return queryset.annotate(avg_rating=Avg("reviews__rating")).filter(
            avg_rating__gte=value
        )

    def filter_max_rating(self, queryset, name, value):
        """Filter products by maximum average rating."""
        return queryset.annotate(avg_rating=Avg("reviews__rating")).filter(
            avg_rating__lte=value
        )

    def filter_category_tree(self, queryset, name, value):
        """
        Filter products by category slug including all subcategories.
        """
        try:
            category = Category.objects.get(slug=value)
            # Get all subcategories recursively
            category_ids = [category.id]
            self._get_subcategory_ids(category, category_ids)
            return queryset.filter(categories__id__in=category_ids).distinct()
        except Category.DoesNotExist:
            return queryset.none()

    def _get_subcategory_ids(self, category, category_ids):
        """Helper method to recursively get all subcategories."""
        children = Category.objects.filter(parent=category)
        for child in children:
            category_ids.append(child.id)
            self._get_subcategory_ids(child, category_ids)

    def filter_in_stock(self, queryset, name, value):
        """Filter products by stock availability."""
        if value:
            return queryset.filter(stock_quantity__gt=0)
        return queryset.filter(stock_quantity=0)

    def filter_has_variants(self, queryset, name, value):
        """Filter products that have variants or not."""
        if value:
            return queryset.annotate(variant_count=Count("variants")).filter(
                variant_count__gt=0
            )
        return queryset.annotate(variant_count=Count("variants")).filter(
            variant_count=0
        )

    def filter_variant_attribute(self, queryset, name, value):
        """
        Filter products by variant attribute.
        Format: attribute_name:attribute_value (e.g., color:red)
        """
        if ":" not in value:
            return queryset

        attr_name, attr_value = value.split(":", 1)
        # Django JSON field lookup for attributes of variants
        return queryset.filter(
            variants__attributes__contains={attr_name: attr_value}
        ).distinct()

    def filter_min_reviews(self, queryset, name, value):
        """Filter products that have at least a certain number of reviews."""
        return queryset.annotate(review_count=Count("reviews")).filter(
            review_count__gte=value
        )

    def filter_is_on_sale(self, queryset, name, value):
        """Filter products that are on sale."""
        if value:
            return queryset.exclude(compare_at_price__isnull=True).filter(
                compare_at_price__gt=0, compare_at_price__gt="price"
            )
        return queryset.filter(compare_at_price__isnull=True).distinct()

    def filter_is_new(self, queryset, name, value):
        """
        Filter products that are new (created within the last 30 days).
        """
        from django.utils import timezone
        import datetime

        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

        if value:
            return queryset.filter(created_at__gte=thirty_days_ago)
        return queryset.filter(created_at__lt=thirty_days_ago)

    def filter_search(self, queryset, name, value):
        """
        Comprehensive search across product fields.
        """
        if not value:
            return queryset

        # Split the search query into terms
        terms = value.split()

        # Start with an empty queryset
        query = queryset.none()

        # For each term, search across multiple fields
        for term in terms:
            term_query = (
                queryset.filter(
                    # Search in basic fields
                    name__icontains=term
                )
                | queryset.filter(description__icontains=term)
                | queryset.filter(sku__icontains=term)
                | queryset.filter(
                    # Search in category names
                    categories__name__icontains=term
                )
                | queryset.filter(
                    # Search in variant names
                    variants__name__icontains=term
                )
                | queryset.filter(
                    # Search in review content
                    reviews__content__icontains=term
                )
            )

            # Union with the results for this term
            query = query | term_query

        # Return distinct results
        return query.distinct()

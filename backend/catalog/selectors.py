"""Product queries used by the API (req 7: search by name/description, sort by price/popularity)."""
from django.db.models import Q

SORTS = {
    "price_asc": ["price", "id"],
    "price_desc": ["-price", "id"],
    "popularity": ["-popularity", "id"],
}


def search_products(queryset, q="", category="", brand="", family="", sort="popularity"):
    """Out-of-stock products are deliberately kept in the results."""
    q = (q or "").strip()
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__name__icontains=q)
        )
    if category:
        queryset = queryset.filter(category__slug=category)
    if brand:
        queryset = queryset.filter(brand__name=brand)
    if family:
        queryset = queryset.filter(families__name=family)
    return queryset.order_by(*SORTS.get(sort, SORTS["popularity"])).distinct()

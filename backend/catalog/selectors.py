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


def filter_options():
    """Everything the shop's filter sidebar needs, straight from the database.

    Replaces the frontend's hard-coded mock lists. Only brands/families that have at
    least one active product are listed, each with how many products it has.
    """
    from django.db.models import Count, Q

    from .models import Brand, Category, NoteFamily

    active = Q(products__active=True)
    def rows(model):
        return [
            {"name": row.name, "count": row.n}
            for row in model.objects.annotate(n=Count("products", filter=active)).filter(n__gt=0).order_by("name")
        ]
    return {
        "categories": [
            {"slug": c.slug, "name": c.name, "count": c.n}
            for c in Category.objects.annotate(n=Count("products", filter=active)).order_by("name")
        ],
        "brands": rows(Brand),
        "families": rows(NoteFamily),
    }

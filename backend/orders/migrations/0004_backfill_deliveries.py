"""Give every order line a delivery row (req 3, 12).

Checkout (orders.services.place_order) always creates one Delivery per OrderItem, but
orders inserted by other means (demo data, old scripts) had none. The product manager's
delivery list reads Delivery rows, so those orders were invisible there while the
customer still saw them in their order history. This backfills the missing rows.
"""
from django.db import migrations

DONE = ("delivered", "refunded")


def backfill(apps, schema_editor):
    OrderItem = apps.get_model("orders", "OrderItem")
    Delivery = apps.get_model("orders", "Delivery")
    missing = OrderItem.objects.filter(delivery__isnull=True).select_related("order")
    Delivery.objects.bulk_create(
        Delivery(
            order_item=item,
            delivery_address=item.order.shipping_address,
            completed=item.order.status in DONE,
        )
        for item in missing.iterator()
    )


class Migration(migrations.Migration):
    dependencies = [("orders", "0003_invoice_counter")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]

"""Re-send an order's invoice PDF by email, e.g. to check the SMTP settings.

    python manage.py send_invoice_email 12
    python manage.py send_invoice_email 12 --to me@example.com
"""
from django.core.management.base import BaseCommand, CommandError

from orders.invoices import seal_and_email
from orders.models import Invoice


class Command(BaseCommand):
    help = "Email the invoice PDF of an order to its customer (or to --to)."

    def add_arguments(self, parser):
        parser.add_argument("order_id", type=int)
        parser.add_argument("--to", help="send to this address instead of the customer")

    def handle(self, order_id, to=None, **options):
        invoice = Invoice.objects.select_related("order__user").filter(order_id=order_id).first()
        if invoice is None:
            raise CommandError(f"Order {order_id} has no invoice.")
        seal_and_email(invoice, to=to)
        self.stdout.write(self.style.SUCCESS(f"Sent {invoice.number} to {to or invoice.order.user.email}"))

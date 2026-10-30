"""One demo account per role, matching the frontend's demo users. Safe to re-run."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Role
from payments.models import CreditCard

PASSWORD = "Demo1234"
DEMO_USERS = [
    ("customer@demo.com", Role.CUSTOMER, "Alice Customer", "11111111111", "Kadikoy, Istanbul"),
    ("sales@demo.com", Role.SALES_MANAGER, "Sarah Sales", "", ""),
    ("product@demo.com", Role.PRODUCT_MANAGER, "Paul Product", "", ""),
    ("support@demo.com", Role.SUPPORT_AGENT, "Sam Support", "", ""),
]


class Command(BaseCommand):
    help = "Create demo users for every role (password: Demo1234) and a saved card for the customer."

    def handle(self, *args, **options):
        User = get_user_model()
        for email, role, name, tax_id, address in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=email, defaults=dict(role=role, name=name, tax_id=tax_id, home_address=address),
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
            self.stdout.write(f"{'created' if created else 'exists '}  {email:20} {role}")
        customer = User.objects.get(email="customer@demo.com")
        if not customer.cards.exists():
            CreditCard.from_number(customer, "4242424242424242", "Alice Customer", 12, 2030, brand="Visa")
            self.stdout.write("saved demo card 4242 4242 4242 4242 for the customer (a card ending 0002 is declined)")

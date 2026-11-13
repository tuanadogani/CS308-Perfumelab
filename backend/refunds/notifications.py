import logging
from functools import partial

from django.core.mail import send_mail
from django.db import transaction

from wishlist.models import Notification

log = logging.getLogger(__name__)


def notify_refund_approved(refund, payment_refund):
    """Called inside the locked approval transaction, once payment has succeeded."""
    item = refund.order_item
    order = item.order
    amount = f"{payment_refund.amount:.2f} TL"
    # Keep the persistent message within Notification.message's 300-character limit.
    message = (
        f"Your refund for {item.product.name[:120]} (order #{order.pk}) was approved. "
        f"Refunded amount: {amount}."
    )
    Notification.objects.create(user_id=order.user_id, product_id=item.product_id, message=message)
    body = (
        f"Your refund request #{refund.pk} for order #{order.pk} was approved.\n\n"
        f"Product: {item.product.name}\n"
        f"Quantity: {item.quantity}\n"
        f"Refunded amount: {amount}\n"
        "The refund was issued to the original payment method.\n"
        f"Refund reference: {payment_refund.transaction_id}\n"
    )
    transaction.on_commit(
        partial(_send_approval_email, order.user.email, body, refund.pk), robust=True
    )


def _send_approval_email(recipient, body, refund_id):
    """Email is best effort; the committed refund and in-app alert must survive SMTP failures."""
    try:
        sent = send_mail("Your refund was approved", body, None, [recipient], fail_silently=False)
        if not sent:
            log.warning("Refund approval email was not sent for request %s", refund_id)
    except Exception:
        log.exception("Refund approval email failed for request %s", refund_id)

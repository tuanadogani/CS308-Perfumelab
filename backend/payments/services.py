import logging

from django.db import transaction

from orders.invoices import seal_and_email
from orders.services import place_order

from . import bank
from .models import Payment

log = logging.getLogger(__name__)


def checkout(user, cart, card, card_number, shipping_address=None):
    """Pay and place the order as one unit (req 4).

    The order, stock change and payment all happen in one transaction: if the bank
    declines, nothing is kept and the cart stays as it was. The invoice email goes out
    only after the transaction has committed.
    """
    if card.user_id != user.pk or not card.matches(card_number):
        raise bank.PaymentDeclined("Card details do not match the saved card.")
    with transaction.atomic():
        order = place_order(user, cart, card=card, shipping_address=shipping_address)
        txn = bank.charge(card_number, order.total)
        Payment.objects.create(order=order, card=card, amount=order.total, transaction_id=txn)
        transaction.on_commit(lambda: _send_invoice(order))
    return order


def _send_invoice(order):
    try:
        seal_and_email(order.invoice)
    except Exception:  # the order is already paid; a mail problem must not undo it
        log.exception("Invoice email failed for order %s", order.pk)

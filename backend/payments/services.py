import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from orders.invoices import seal_and_email
from orders.services import place_order

from . import bank
from .models import Payment, PaymentRefund

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


@transaction.atomic
def refund_payment(refund):
    """Refund a locked request; decide_refund owns lifecycle/permission checks.

    Lock the original payment to serialize partial refunds and cap the cumulative
    amount. A saved confirmation is returned without calling the bank again.
    """
    try:
        payment = Payment.objects.select_for_update().get(order_id=refund.order_item.order_id)
    except Payment.DoesNotExist:
        raise ValidationError("The order has no recorded payment to refund.")
    existing = PaymentRefund.objects.filter(refund_request=refund).first()
    if existing:
        return existing
    refunded = payment.refunds.aggregate(total=Sum("amount"))["total"] or 0
    if refund.amount < 0 or refunded + refund.amount > payment.amount:
        raise ValidationError("The refund would exceed the original payment amount.")
    transaction_id = bank.refund(
        payment.transaction_id, refund.amount, idempotency_key=f"refund-request-{refund.pk}"
    )
    return PaymentRefund.objects.create(
        refund_request=refund, payment=payment, amount=refund.amount, transaction_id=transaction_id
    )

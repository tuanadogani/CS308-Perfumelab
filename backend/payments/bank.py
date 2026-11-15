"""Mock banking entity. Real card verification and limits are out of scope (req 15)."""
import uuid


class PaymentDeclined(Exception):
    pass


class RefundDeclined(Exception):
    pass


# Demo cards ending in these digits are declined, so the failure path can be shown live.
DECLINED_LAST4 = {"0002"}


def charge(card_number, amount):
    """Return a transaction id, or raise PaymentDeclined."""
    digits = "".join(ch for ch in card_number if ch.isdigit())
    if digits[-4:] in DECLINED_LAST4:
        raise PaymentDeclined("The bank declined this card.")
    return f"TXN-{uuid.uuid4().hex[:24].upper()}"


def refund(transaction_id, amount, *, idempotency_key):
    """Mock a credit to the original charge, without needing card details again.

    The same charge/key yields the same confirmation on retry, including after a
    local transaction rollback. This is a simulation; no real bank is contacted.
    """
    if not transaction_id or not idempotency_key or not amount.is_finite() or amount < 0:
        raise RefundDeclined("Invalid refund details.")
    reference = uuid.uuid5(uuid.NAMESPACE_URL, f"perfumelab:refund:{transaction_id}:{idempotency_key}")
    return f"RFND-{reference.hex[:24].upper()}"

"""Mock banking entity. Real card verification and limits are out of scope (req 15)."""
import uuid


class PaymentDeclined(Exception):
    pass


# Demo cards ending in these digits are declined, so the failure path can be shown live.
DECLINED_LAST4 = {"0002"}


def charge(card_number, amount):
    """Return a transaction id, or raise PaymentDeclined."""
    digits = "".join(ch for ch in card_number if ch.isdigit())
    if digits[-4:] in DECLINED_LAST4:
        raise PaymentDeclined("The bank declined this card.")
    return f"TXN-{uuid.uuid4().hex[:24].upper()}"

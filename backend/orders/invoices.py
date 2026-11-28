"""Invoice PDF: rendered on demand from the database, only its SHA-256 is stored."""
import hashlib
import io
from pathlib import Path


from django.conf import settings
from django.core.mail import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Helvetica has no ş, ğ, ı, İ: Turkish names and addresses came out as black boxes.
FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT, FONT_BOLD = "DejaVuSans", "DejaVuSans-Bold"

def _register_fonts():
    if FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT, str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf")))

# Page layout. Long text is wrapped and long orders continue on a new page instead of
# running off the paper.
LEFT, RIGHT, BOTTOM = 20 * mm, 190 * mm, 20 * mm
LINE = 6 * mm
PRODUCT_WIDTH = 88 * mm  # the product column ends just before the Qty column at 110 mm


def wrap_text(text, font, size, width):
    """Split text into lines no wider than `width` (breaks at spaces)."""
    return simpleSplit(text, font, size, width) or [""]


def render_invoice_pdf(invoice):
    _register_fonts()
    order = invoice.order
    buf = io.BytesIO()
    # invariant=1 keeps the file byte-identical between renders, so the stored hash stays valid
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    width, height = A4
    top = height - 25 * mm
    y = top

    def table_header(y):
        c.setFont(FONT_BOLD, 10)
        for x, label in ((20, "Product"), (110, "Qty"), (130, "Unit price"), (165, "Total")):
            c.drawString(x * mm, y, label)
        y -= 2 * mm
        c.line(LEFT, y, RIGHT, y)
        c.setFont(FONT, 10)
        return y - LINE

    c.setFont(FONT_BOLD, 20)
    c.drawString(LEFT, y, f"{settings.STORE_NAME} - Invoice")
    y -= 10 * mm
    c.setFont(FONT, 10)
    for line in (
        f"Invoice no: {invoice.number}",
        f"Date: {invoice.issued_at:%Y-%m-%d %H:%M}",
        f"Customer: {order.user.name or order.user.email} ({order.user.email})",
        f"Delivery address: {order.shipping_address}",
        f"Payment: card ending {order.card_last4 or '----'}",
    ):
        for part in wrap_text(line, FONT, 10, RIGHT - LEFT):
            c.drawString(LEFT, y, part)
            y -= LINE

    y -= LINE
    y = table_header(y)
    for item in order.items.select_related("product__brand"):
        name = f"{item.product.brand.name} {item.product.name} {item.product.volume_ml}ml"
        name_lines = wrap_text(name, FONT, 10, PRODUCT_WIDTH)
        if y - (len(name_lines) - 1) * LINE < BOTTOM:
            c.showPage()
            y = table_header(top)
        c.drawString(110 * mm, y, str(item.quantity))
        c.drawString(130 * mm, y, f"{item.unit_price:.2f} TL")
        c.drawString(165 * mm, y, f"{item.line_total:.2f} TL")
        for part in name_lines:
            c.drawString(LEFT, y, part)
            y -= LINE

    if y - 8 * mm < BOTTOM:
        c.showPage()
        y = top
    c.line(LEFT, y, RIGHT, y)
    y -= 8 * mm
    c.setFont(FONT_BOLD, 12)
    c.drawString(130 * mm, y, f"TOTAL: {invoice.total:.2f} TL")
    c.showPage()
    c.save()
    return buf.getvalue()


def invoice_email_body(invoice):
    order = invoice.order
    lines = [f"Hello {order.user.name or order.user.email},", "",
             f"Thank you for your order #{order.pk}. Your invoice {invoice.number} is attached as a PDF.", ""]
    for item in order.items.select_related("product__brand"):
        lines.append(f"  {item.quantity} x {item.product.brand.name} {item.product.name} - {item.line_total:.2f} TL")
    lines += ["", f"Total: {invoice.total:.2f} TL", f"Delivery address: {order.shipping_address}", "", settings.STORE_NAME]
    return "\n".join(lines)


def seal_and_email(invoice, to=None):
    """Store the PDF's hash and email the PDF copy to the customer (req 4).

    `to` overrides the recipient (used by the send_invoice_email command for testing).
    """
    pdf = render_invoice_pdf(invoice)
    invoice.pdf_sha256 = hashlib.sha256(pdf).hexdigest()
    invoice.save(update_fields=["pdf_sha256"])
    message = EmailMessage(
        subject=f"Your {settings.STORE_NAME} invoice {invoice.number}",
        body=invoice_email_body(invoice),
        to=[to or invoice.order.user.email],
    )
    message.attach(f"{invoice.number}.pdf", pdf, "application/pdf")
    message.send()
    return pdf

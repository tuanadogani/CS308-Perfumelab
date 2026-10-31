"""Invoice PDF: rendered on demand from the database, only its SHA-256 is stored."""
import hashlib
import io

from django.core.mail import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def render_invoice_pdf(invoice):
    order = invoice.order
    buf = io.BytesIO()
    # invariant=1 keeps the file byte-identical between renders, so the stored hash stays valid
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    width, height = A4
    y = height - 25 * mm

    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, y, "PerfumeLab - Invoice")
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    for line in (
        f"Invoice no: {invoice.number}",
        f"Date: {invoice.issued_at:%Y-%m-%d %H:%M}",
        f"Customer: {order.user.name or order.user.email} ({order.user.email})",
        f"Delivery address: {order.shipping_address}",
        f"Payment: card ending {order.card_last4 or '----'}",
    ):
        c.drawString(20 * mm, y, line)
        y -= 6 * mm

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    for x, label in ((20, "Product"), (110, "Qty"), (130, "Unit price"), (165, "Total")):
        c.drawString(x * mm, y, label)
    y -= 2 * mm
    c.line(20 * mm, y, 190 * mm, y)
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    for item in order.items.select_related("product__brand"):
        c.drawString(20 * mm, y, f"{item.product.brand.name} {item.product.name} {item.product.volume_ml}ml"[:55])
        c.drawString(110 * mm, y, str(item.quantity))
        c.drawString(130 * mm, y, f"{item.unit_price:.2f} TL")
        c.drawString(165 * mm, y, f"{item.line_total:.2f} TL")
        y -= 6 * mm

    c.line(20 * mm, y, 190 * mm, y)
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(130 * mm, y, f"TOTAL: {invoice.total:.2f} TL")
    c.showPage()
    c.save()
    return buf.getvalue()


def seal_and_email(invoice):
    """Store the PDF's hash and email the PDF copy to the customer (req 4)."""
    pdf = render_invoice_pdf(invoice)
    invoice.pdf_sha256 = hashlib.sha256(pdf).hexdigest()
    invoice.save(update_fields=["pdf_sha256"])
    message = EmailMessage(
        subject=f"Your PerfumeLab invoice {invoice.number}",
        body="Thank you for your order. Your invoice is attached.",
        to=[invoice.order.user.email],
    )
    message.attach(f"{invoice.number}.pdf", pdf, "application/pdf")
    message.send()
    return pdf

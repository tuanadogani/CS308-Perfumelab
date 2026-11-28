"""Invoice PDF content and real SMTP delivery path (Scrum 39).

The SMTP tests swap smtplib.SMTP for a fake server, so they check exactly what Django
would say to Gmail (host, port, STARTTLS, login, message with the PDF) without network.
"""
import email
import email.header
import importlib
import io
import os
from unittest import mock

from django.test import TestCase, override_settings
from pypdf import PdfReader

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from orders.invoices import render_invoice_pdf, seal_and_email
from orders.services import place_order

SMTP = dict(
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
    EMAIL_HOST="smtp.gmail.com", EMAIL_PORT=587, EMAIL_USE_TLS=True, EMAIL_USE_SSL=False,
    EMAIL_HOST_USER="shop@gmail.com", EMAIL_HOST_PASSWORD="app-password", EMAIL_TIMEOUT=10,
    DEFAULT_FROM_EMAIL="Maison Lumière <shop@gmail.com>",
)


def pdf_text(pdf_bytes):
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf_bytes)).pages)


class InvoiceFixture(TestCase):
    def setUp(self):
        self.user = make_user(name="Şükrü Ağaoğlu", home_address="İstiklal Cad. 5, Beyoğlu, İstanbul")
        self.first = make_product(price="1200.00", stock=5, name="Sauvage", brand="Dior")
        self.second = make_product(price="850.50", stock=5, name="Libre", brand="YSL")
        cart = Cart.objects.create(user=self.user)
        add_to_cart(cart, self.first, 2)
        add_to_cart(cart, self.second, 1)
        self.order = place_order(self.user, cart)
        self.invoice = self.order.invoice


class InvoicePdfContentTests(InvoiceFixture):
    def test_pdf_shows_number_customer_lines_and_total(self):
        text = pdf_text(render_invoice_pdf(self.invoice))
        for expected in (self.invoice.number, self.user.email, "Dior Sauvage", "YSL Libre",
                         "2400.00 TL", "850.50 TL", "TOTAL: 3250.50 TL"):
            self.assertIn(expected, text)

    def test_turkish_letters_survive_in_the_pdf(self):
        text = pdf_text(render_invoice_pdf(self.invoice))
        self.assertIn("Şükrü Ağaoğlu", text)
        self.assertIn("Beyoğlu, İstanbul", text)

    def test_pdf_and_email_carry_the_shop_name(self):
        self.assertIn("Maison Lumière - Invoice", pdf_text(render_invoice_pdf(self.invoice)))
        from orders.invoices import invoice_email_body
        self.assertTrue(invoice_email_body(self.invoice).rstrip().endswith("Maison Lumière"))
        self.assertNotIn("PerfumeLab", invoice_email_body(self.invoice))

    def test_pdf_is_a_single_valid_page(self):
        reader = PdfReader(io.BytesIO(render_invoice_pdf(self.invoice)))
        self.assertEqual(len(reader.pages), 1)


class SmtpDeliveryTests(InvoiceFixture):
    @override_settings(**SMTP)
    def test_invoice_goes_through_smtp_with_tls_login_and_pdf(self):
        with mock.patch("smtplib.SMTP") as smtp_class:
            server = smtp_class.return_value
            server.sendmail.return_value = {}
            seal_and_email(self.invoice)

        smtp_class.assert_called_once()
        self.assertEqual(smtp_class.call_args.args, ("smtp.gmail.com", 587))
        self.assertEqual(smtp_class.call_args.kwargs["timeout"], 10)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("shop@gmail.com", "app-password")
        sender, recipients, raw = server.sendmail.call_args.args
        self.assertIn("shop@gmail.com", sender)
        self.assertEqual(recipients, [self.user.email])
        message = email.message_from_bytes(raw)
        self.assertIn(f"Maison Lumière invoice {self.invoice.number}", str(email.header.make_header(email.header.decode_header(message["Subject"]))))
        attachments = [p for p in message.walk() if p.get_content_type() == "application/pdf"]
        self.assertEqual(attachments[0].get_filename(), f"{self.invoice.number}.pdf")
        self.assertTrue(attachments[0].get_payload(decode=True).startswith(b"%PDF"))

    @override_settings(**SMTP)
    def test_smtp_failure_is_raised_to_the_caller(self):
        # payments.services._send_invoice catches this so a paid order is never undone
        import smtplib
        with mock.patch("smtplib.SMTP") as smtp_class:
            smtp_class.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad")
            with self.assertRaises(smtplib.SMTPAuthenticationError):
                seal_and_email(self.invoice)


class EmailSettingsFromEnvTests(TestCase):
    def load_settings(self, env):
        import config.settings as settings_module
        with mock.patch.dict(os.environ, env):
            return importlib.reload(settings_module)

    def tearDown(self):
        import config.settings as settings_module
        importlib.reload(settings_module)  # back to the real environment

    def test_console_backend_by_default(self):
        env = {k: v for k, v in os.environ.items() if k != "EMAIL_BACKEND"}
        with mock.patch.dict(os.environ, env, clear=True):
            import config.settings as settings_module
            loaded = importlib.reload(settings_module)
        self.assertEqual(loaded.EMAIL_BACKEND, "django.core.mail.backends.console.EmailBackend")

    def test_gmail_settings_are_read_from_env(self):
        loaded = self.load_settings({
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "EMAIL_HOST": "smtp.gmail.com", "EMAIL_PORT": "587", "EMAIL_USE_TLS": "true",
            "EMAIL_HOST_USER": "shop@gmail.com",
        })
        self.assertEqual((loaded.EMAIL_HOST, loaded.EMAIL_PORT, loaded.EMAIL_USE_TLS),
                         ("smtp.gmail.com", 587, True))
        self.assertEqual(loaded.EMAIL_HOST_USER, "shop@gmail.com")

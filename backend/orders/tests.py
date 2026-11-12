import threading
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase
from reportlab.pdfbase import pdfmetrics

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user

from .invoices import FONT, FONT_BOLD, render_invoice_pdf
from refunds.models import RefundRequest

from .models import Delivery, Order, OrderItem, OrderStatus
from .services import advance_status, cancel_order, place_order


def cart_with(user, product, qty=1):
    cart, _ = Cart.objects.get_or_create(user=user)
    add_to_cart(cart, product, qty)
    return cart


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(price="1000.00", stock=5, popularity=0)

    def test_stock_decreases_and_popularity_grows(self):
        place_order(self.user, cart_with(self.user, self.product, 2))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.product.popularity, 2)

    def test_order_snapshots_price_and_total(self):
        order = place_order(self.user, cart_with(self.user, self.product, 2))
        self.product.apply_discount(50)  # later price change must not touch the old order
        item = order.items.get()
        self.assertEqual(item.unit_price, 1000)
        self.assertEqual(order.total, 2000)
        self.assertEqual(item.unit_cost, 500)

    def test_creates_invoice_delivery_and_clears_cart(self):
        cart = cart_with(self.user, self.product)
        order = place_order(self.user, cart)
        self.assertTrue(order.invoice.number.startswith("INV-"))
        self.assertFalse(Delivery.objects.get(order_item__order=order).completed)
        self.assertEqual(cart.items.count(), 0)
        self.assertEqual(order.status, OrderStatus.PROCESSING)

    def test_empty_cart_rejected(self):
        with self.assertRaises(ValidationError):
            place_order(self.user, Cart.objects.create(user=self.user))

    def test_missing_address_rejected(self):
        user = make_user(home_address="")
        with self.assertRaises(ValidationError):
            place_order(user, cart_with(user, self.product))

    def test_insufficient_stock_rolls_everything_back(self):
        cart = cart_with(self.user, self.product, 3)
        self.product.__class__.objects.filter(pk=self.product.pk).update(stock=1)
        with self.assertRaises(ValidationError):
            place_order(self.user, cart)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)


class LifecycleTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(stock=5)
        self.order = place_order(self.user, cart_with(self.user, self.product, 2))

    def test_cancel_processing_order_restocks(self):
        cancel_order(self.order)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)
        self.assertEqual(self.product.stock, 5)

    def test_cannot_cancel_after_shipping(self):
        advance_status(self.order)
        with self.assertRaises(ValidationError):
            cancel_order(self.order)

    def test_cannot_cancel_twice(self):
        cancel_order(self.order)
        with self.assertRaises(ValidationError):
            cancel_order(self.order)

    def test_status_moves_processing_to_delivered(self):
        self.assertEqual(advance_status(self.order).status, OrderStatus.IN_TRANSIT)
        delivered = advance_status(self.order)
        self.assertEqual(delivered.status, OrderStatus.DELIVERED)
        self.assertIsNotNone(delivered.delivered_at)
        self.assertTrue(Delivery.objects.get(order_item__order=delivered).completed)

    def test_cannot_advance_past_delivered(self):
        advance_status(self.order)
        advance_status(self.order)
        with self.assertRaises(ValidationError):
            advance_status(self.order)

    def test_delivery_list_properties(self):
        d = Delivery.objects.get(order_item__order=self.order)
        self.assertEqual((d.customer_id, d.product_id, d.quantity), (self.user.pk, self.product.pk, 2))
        self.assertEqual(d.total_price, self.order.total)


class ConcurrencyTests(TransactionTestCase):
    """Req 18: two customers racing for the last bottle - exactly one may win."""

    def test_last_bottle_sold_only_once(self):
        product = make_product(stock=1)
        users = [make_user() for _ in range(4)]
        carts = [cart_with(u, product) for u in users]
        results, barrier = [], threading.Barrier(len(users))

        def buy(user, cart):
            try:
                barrier.wait()
                place_order(user, cart)
                results.append("ok")
            except ValidationError:
                results.append("rejected")
            finally:
                connection.close()

        threads = [threading.Thread(target=buy, args=(u, c)) for u, c in zip(users, carts)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        product.refresh_from_db()
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)


from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase


class SalesInvoiceApiTests(APITestCase):
    def setUp(self):
        self.sales_manager = make_user("sales_manager")
        self.customer = make_user("customer", name="Ross Geller", tax_id="12345678901")
        self.product_manager = make_user("product_manager")
        self.product = make_product(name="Bleu de Chanel", price="1000.00", stock=10)
        self.order = place_order(self.customer, cart_with(self.customer, self.product, 2))
        self.invoice = self.order.invoice

    def test_requires_authentication(self):
        response = self.client.get("/api/sales/invoices/")
        self.assertEqual(response.status_code, 401)
        response = self.client.get(f"/api/sales/invoices/{self.invoice.id}/")
        self.assertEqual(response.status_code, 401)
        response = self.client.get(f"/api/sales/invoices/{self.invoice.id}/pdf/")
        self.assertEqual(response.status_code, 401)

    def test_forbidden_for_customers_and_product_managers(self):
        for user in (self.customer, self.product_manager):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/sales/invoices/").status_code, 403)
            self.assertEqual(self.client.get(f"/api/sales/invoices/{self.invoice.id}/").status_code, 403)
            self.assertEqual(self.client.get(f"/api/sales/invoices/{self.invoice.id}/pdf/").status_code, 403)

    def test_sales_manager_can_list_invoices(self):
        self.client.force_authenticate(self.sales_manager)
        response = self.client.get("/api/sales/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        data = response.data[0]
        self.assertEqual(data["id"], self.invoice.id)
        self.assertEqual(data["number"], self.invoice.number)
        self.assertEqual(data["total"], 2000.0)
        self.assertEqual(data["customer"]["email"], self.customer.email)
        self.assertEqual(data["customer"]["taxId"], "12345678901")
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["productName"], "Bleu de Chanel")
        self.assertEqual(data["items"][0]["quantity"], 2)

    def test_filter_invoices_by_date_range(self):
        self.client.force_authenticate(self.sales_manager)
        # Create an older order from 10 days ago
        old_order = place_order(self.customer, cart_with(self.customer, self.product, 1))
        old_invoice = old_order.invoice
        ten_days_ago = timezone.now() - timedelta(days=10)
        old_invoice.__class__.objects.filter(pk=old_invoice.pk).update(issued_at=ten_days_ago)

        today_str = timezone.now().date().isoformat()
        # Query only today
        response = self.client.get(f"/api/sales/invoices/?start_date={today_str}&end_date={today_str}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.invoice.id)

        # Query camelCase startDate / endDate across the whole range
        start_str = (timezone.now() - timedelta(days=15)).date().isoformat()
        response = self.client.get(f"/api/sales/invoices/?startDate={start_str}&endDate={today_str}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_invalid_date_format_returns_400(self):
        self.client.force_authenticate(self.sales_manager)
        response = self.client.get("/api/sales/invoices/?start_date=not-a-date")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid date format", response.data["message"])

    def test_retrieve_single_invoice(self):
        self.client.force_authenticate(self.sales_manager)
        response = self.client.get(f"/api/sales/invoices/{self.invoice.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["number"], self.invoice.number)

    def test_invoice_pdf_view_and_download(self):
        self.client.force_authenticate(self.sales_manager)
        # Inline (default for viewing / printing)
        response = self.client.get(f"/api/sales/invoices/{self.invoice.id}/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

        # Attachment (forced download)
        response = self.client.get(f"/api/sales/invoices/{self.invoice.id}/pdf/?download=true")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])


class SalesAnalyticsApiTests(APITestCase):
    def setUp(self):
        self.sales_manager = make_user("sales_manager")
        self.customer = make_user("customer", name="Ross Geller")
        self.product_manager = make_user("product_manager")
        # Product with default cost (50% = 500)
        self.p_default = make_product(name="Bleu de Chanel", price="1000.00", stock=10)
        # Product with specified custom cost (700)
        self.p_custom = make_product(name="Sauvage", price="1000.00", cost="700.00", stock=10)

    def test_requires_authentication(self):
        response = self.client.get("/api/sales/analytics/")
        self.assertEqual(response.status_code, 401)

    def test_forbidden_for_customers_and_product_managers(self):
        for user in (self.customer, self.product_manager):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/sales/analytics/").status_code, 403)
            self.assertEqual(self.client.get("/api/sales/revenue/").status_code, 403)

    def test_revenue_and_profit_calculation_with_default_cost(self):
        # 2 units of p_default (unit_price=1000, unit_cost=500)
        place_order(self.customer, cart_with(self.customer, self.p_default, 2))
        self.client.force_authenticate(self.sales_manager)

        response = self.client.get("/api/sales/analytics/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["totalOrders"], 1)
        self.assertEqual(response.data["totalRevenue"], 2000.0)
        self.assertEqual(response.data["totalCost"], 1000.0)
        self.assertEqual(response.data["profit"], 1000.0)
        self.assertTrue(response.data["isProfit"])
        self.assertEqual(response.data["profitMargin"], 50.0)

    def test_revenue_and_profit_with_custom_product_cost(self):
        # 1 unit of p_custom (unit_price=1000, unit_cost=700)
        place_order(self.customer, cart_with(self.customer, self.p_custom, 1))
        self.client.force_authenticate(self.sales_manager)

        response = self.client.get("/api/sales/revenue/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["totalRevenue"], 1000.0)
        self.assertEqual(response.data["totalCost"], 700.0)
        self.assertEqual(response.data["profit"], 300.0)
        self.assertEqual(response.data["profitMargin"], 30.0)

    def test_cancelled_orders_excluded_from_analytics(self):
        order = place_order(self.customer, cart_with(self.customer, self.p_default, 1))
        cancel_order(order)
        self.client.force_authenticate(self.sales_manager)

        response = self.client.get("/api/sales/analytics/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["totalOrders"], 0)
        self.assertEqual(response.data["totalRevenue"], 0.0)
        self.assertEqual(response.data["totalCost"], 0.0)
        self.assertEqual(response.data["profit"], 0.0)

    def test_date_range_filtering_and_chart_data(self):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        # Order today
        place_order(self.customer, cart_with(self.customer, self.p_default, 1))

        self.client.force_authenticate(self.sales_manager)
        response = self.client.get(f"/api/sales/analytics/?start_date={yesterday.isoformat()}&end_date={today.isoformat()}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["startDate"], yesterday.isoformat())
        self.assertEqual(response.data["endDate"], today.isoformat())

        chart = response.data["chartData"]
        self.assertEqual(len(chart), 2)
        # Yesterday had 0 orders
        self.assertEqual(chart[0]["date"], yesterday.isoformat())
        self.assertEqual(chart[0]["revenue"], 0.0)
        self.assertEqual(chart[0]["orderCount"], 0)
        # Today had 1 order
        self.assertEqual(chart[1]["date"], today.isoformat())
        self.assertEqual(chart[1]["revenue"], 1000.0)
        self.assertEqual(chart[1]["cost"], 500.0)
        self.assertEqual(chart[1]["profit"], 500.0)
        self.assertEqual(chart[1]["orderCount"], 1)

    def test_invalid_date_order_returns_400(self):
        self.client.force_authenticate(self.sales_manager)
        response = self.client.get("/api/sales/analytics/?start_date=2026-11-10&end_date=2026-11-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_date cannot be after end_date", response.data["message"])


class InvoicePdfTests(TestCase):
    def setUp(self):
        self.user = make_user(name="Ayşe Yılmaz", home_address="Çırağan Cd. No:5, Beşiktaş, İstanbul")
        self.order = place_order(self.user, cart_with(self.user, make_product(stock=5)))

    def test_invoice_fonts_have_turkish_letters(self):
        render_invoice_pdf(self.order.invoice)
        for name in (FONT, FONT_BOLD):
            glyphs = pdfmetrics.getFont(name).face.charToGlyph
            for ch in "çğıİöşüÇĞÖŞÜ":
                self.assertIn(ord(ch), glyphs, f"{name} is missing {ch}")

    def test_invoice_embeds_unicode_font(self):
        self.assertIn(FONT.encode(), render_invoice_pdf(self.order.invoice))

    def test_invoice_render_is_deterministic(self):
        # the stored SHA-256 only stays valid if every render is byte-identical
        self.assertEqual(render_invoice_pdf(self.order.invoice), render_invoice_pdf(self.order.invoice))


class CustomerOrderApiTests(APITestCase):
    def setUp(self):
        self.user, self.other = make_user(), make_user()
        self.product = make_product(stock=10)
        self.order = place_order(self.user, cart_with(self.user, self.product, 2))
        self.item = self.order.items.get()
        self.base = f"/api/orders/{self.order.pk}/"
        self.refund_url = f"{self.base}items/{self.item.pk}/refund/"
        self.client.force_authenticate(self.user)
        self.routes = [("get", "/api/orders/"), ("get", self.base),
                       ("post", self.base + "cancel/"), ("post", self.refund_url)]

    def deliver(self):
        advance_status(self.order)
        advance_status(self.order)

    def test_authentication_required(self):
        self.client.force_authenticate(None)
        for method, url in self.routes:
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 401)

    def test_staff_roles_rejected(self):
        for role in ("sales_manager", "product_manager", "support_agent"):
            self.client.force_authenticate(make_user(role))
            for method, url in self.routes:
                with self.subTest(role=role, url=url):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 403)

    def test_history_is_owned_and_newest_first(self):
        place_order(self.other, cart_with(self.other, self.product))
        newer = place_order(self.user, cart_with(self.user, self.product))
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [newer.pk, self.order.pk])

    def test_empty_history(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/orders/").data, [])

    def test_detail_preserves_purchase_price_and_hides_cost(self):
        self.product.apply_discount(50)
        response = self.client.get(self.base)
        self.assertEqual(response.status_code, 200)
        item = response.data["items"][0]
        self.assertEqual(item["unitPrice"], "1000.00")
        self.assertEqual(item["lineTotal"], "2000.00")
        self.assertIsNone(item["refund"])
        self.assertNotIn("unitCost", item)
        self.assertNotIn("unit_cost", item)

    def test_other_customers_order_hidden(self):
        self.client.force_authenticate(self.other)
        for method, url in self.routes[1:]:
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 404)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PROCESSING)
        self.assertFalse(RefundRequest.objects.exists())

    def test_cancel_processing_order_once(self):
        response = self.client.post(self.base + "cancel/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], OrderStatus.CANCELLED)
        self.assertEqual(self.client.post(self.base + "cancel/").status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_cancel_rejected_for_other_statuses(self):
        for state in (OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.REFUNDED):
            Order.objects.filter(pk=self.order.pk).update(status=state)
            with self.subTest(state=state):
                self.assertEqual(self.client.post(self.base + "cancel/").status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_refund_requires_delivered(self):
        for state in (OrderStatus.PROCESSING, OrderStatus.IN_TRANSIT, OrderStatus.CANCELLED, OrderStatus.REFUNDED):
            Order.objects.filter(pk=self.order.pk).update(status=state)
            with self.subTest(state=state):
                self.assertEqual(self.client.post(self.refund_url).status_code, 400)
        self.assertFalse(RefundRequest.objects.exists())

    def test_refund_selects_one_line_and_waits_for_approval(self):
        untouched = OrderItem.objects.create(order=self.order, product=make_product(), quantity=1,
                                             unit_price=1000, unit_cost=500)
        self.deliver()
        response = self.client.post(self.refund_url, {"reason": "Not my scent", "amount": "1.00"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["amount"], "2000.00")
        self.assertEqual(response.data["status"], "requested")
        self.assertEqual(response.data["reason"], "Not my scent")
        self.assertFalse(RefundRequest.objects.filter(order_item=untouched).exists())
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)
        items = self.client.get(self.base).data["items"]
        selected = next(item for item in items if item["id"] == self.item.pk)
        self.assertEqual(selected["refund"]["id"], response.data["id"])

    def test_duplicate_request_returns_400(self):
        self.deliver()
        self.assertEqual(self.client.post(self.refund_url).status_code, 201)
        self.assertEqual(self.client.post(self.refund_url).status_code, 400)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_exact_30_day_boundary(self):
        self.deliver()
        now = timezone.now()
        Order.objects.filter(pk=self.order.pk).update(created_at=now - timedelta(days=30))
        with patch("refunds.services.timezone.now", return_value=now):
            self.assertEqual(self.client.post(self.refund_url).status_code, 201)

    def test_expired_purchase_rejected_even_if_delivered_today(self):
        self.deliver()
        now = timezone.now()
        Order.objects.filter(pk=self.order.pk).update(created_at=now - timedelta(days=30, microseconds=1))
        with patch("refunds.services.timezone.now", return_value=now):
            self.assertEqual(self.client.post(self.refund_url).status_code, 400)
        self.assertFalse(RefundRequest.objects.exists())

    def test_item_must_belong_to_url_order(self):
        other_order = place_order(self.user, cart_with(self.user, self.product))
        url = f"/api/orders/{other_order.pk}/items/{self.item.pk}/refund/"
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_campaign_end_does_not_change_refund(self):
        self.product.apply_discount(30)
        order = place_order(self.user, cart_with(self.user, self.product))
        advance_status(order)
        advance_status(order)
        self.product.apply_discount(0)
        url = f"/api/orders/{order.pk}/items/{order.items.get().pk}/refund/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["amount"], "700.00")

    def test_invalid_reason_rejected(self):
        self.deliver()
        self.assertEqual(self.client.post(self.refund_url, {"reason": "x" * 2001}).status_code, 400)
        self.assertFalse(RefundRequest.objects.exists())

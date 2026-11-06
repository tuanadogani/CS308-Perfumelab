import threading

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user

from .models import Delivery, Order, OrderStatus
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


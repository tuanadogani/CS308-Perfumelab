import threading
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from orders.models import Order, OrderStatus
from orders.services import advance_status, place_order
from payments.models import CreditCard, PaymentRefund
from payments.services import checkout
from wishlist.services import set_discount

from .models import RefundRequest, RefundStatus
from .services import decide_refund, receive_return, request_refund


def paid_order(user, cart):
    number = "4242424242424242"
    card = CreditCard.from_number(user, number, "Test Customer", 12, 2030)
    return checkout(user, cart, card, number)


def delivered_order(user, product, qty=1):
    cart = Cart.objects.create(user=user)
    add_to_cart(cart, product, qty)
    order = paid_order(user, cart)
    advance_status(order)
    advance_status(order)
    return order


class RefundTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.sales = make_user("sales_manager")
        self.product = make_product(price="1000.00", stock=5)
        self.order = delivered_order(self.user, self.product, 2)
        self.item = self.order.items.get()

    def test_request_on_delivered_order(self):
        refund = request_refund(self.user, self.item, "Not my scent")
        self.assertEqual(refund.status, RefundStatus.REQUESTED)
        self.assertEqual(refund.amount, 2000)

    def test_not_allowed_before_delivery(self):
        cart, _ = Cart.objects.get_or_create(user=self.user)
        add_to_cart(cart, self.product)
        fresh = place_order(self.user, cart)
        with self.assertRaises(ValidationError):
            request_refund(self.user, fresh.items.get())

    def test_not_allowed_after_30_days(self):
        Order.objects.filter(pk=self.order.pk).update(created_at=timezone.now() - timedelta(days=31))
        self.item.order.refresh_from_db()
        with self.assertRaises(ValidationError):
            request_refund(self.user, self.item)

    def test_allowed_on_day_30(self):
        Order.objects.filter(pk=self.order.pk).update(created_at=timezone.now() - timedelta(days=29))
        self.item.order.refresh_from_db()
        self.assertEqual(request_refund(self.user, self.item).status, RefundStatus.REQUESTED)

    def test_cannot_refund_someone_elses_order(self):
        with self.assertRaises(PermissionDenied):
            request_refund(make_user(), self.item)

    def test_cannot_request_twice(self):
        request_refund(self.user, self.item)
        with self.assertRaises(ValidationError):
            request_refund(self.user, self.item)

    def test_approval_restocks_and_emails_customer(self):
        refund = request_refund(self.user, self.item)
        receive_return(refund, self.sales)
        stock_before = self.product.__class__.objects.get(pk=self.product.pk).stock
        with self.captureOnCommitCallbacks(execute=True):
            decide_refund(refund, self.sales, approve=True)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock_before + 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.REFUNDED)

    def test_rejection_keeps_stock(self):
        refund = request_refund(self.user, self.item)
        stock_before = self.product.__class__.objects.get(pk=self.product.pk).stock
        decide_refund(refund, self.sales, approve=False)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock_before)
        self.assertEqual(len(mail.outbox), 0)

    def test_only_sales_manager_decides(self):
        refund = request_refund(self.user, self.item)
        with self.assertRaises(PermissionDenied):
            decide_refund(refund, make_user("product_manager"), approve=True)

    def test_cannot_decide_twice(self):
        refund = request_refund(self.user, self.item)
        receive_return(refund, self.sales)
        decide_refund(refund, self.sales, approve=True)
        with self.assertRaises(ValidationError):
            decide_refund(refund, self.sales, approve=True)


class DiscountedRefundTests(TestCase):
    def test_refund_uses_price_paid_even_after_campaign_ends(self):
        user, sales = make_user(), make_user("sales_manager")
        product = make_product(price="1000.00")
        set_discount(sales, [product], 30)  # campaign running
        order = delivered_order(user, product)
        set_discount(sales, [product], 0)  # campaign over, price back to 1000
        refund = request_refund(user, order.items.get())
        self.assertEqual(refund.amount, 700)


class SalesRefundApiTests(APITestCase):
    def setUp(self):
        self.customer = make_user(name="Test Customer")
        self.sales = make_user("sales_manager")
        self.product = make_product(stock=5)
        self.order = delivered_order(self.customer, self.product, 2)
        self.refund = request_refund(self.customer, self.order.items.get(), "Not my scent")
        self.base = f"/api/sales/refunds/{self.refund.pk}/"
        self.client.force_authenticate(self.sales)

    def test_authentication_required(self):
        self.client.force_authenticate(None)
        for method, url in [("get", "/api/sales/refunds/"), ("get", self.base),
                            ("post", self.base + "receive/"), ("post", self.base + "decision/")]:
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 401)

    def test_other_roles_cannot_read_or_decide(self):
        for role in ("customer", "product_manager", "support_agent"):
            self.client.force_authenticate(make_user(role))
            for method, url in [("get", "/api/sales/refunds/"), ("get", self.base),
                                ("post", self.base + "receive/"), ("post", self.base + "decision/")]:
                with self.subTest(role=role, url=url):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 403)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, RefundStatus.REQUESTED)
        self.assertIsNone(self.refund.received_at)

    def test_list_detail_and_status_filter(self):
        other = make_user()
        other_order = delivered_order(other, make_product())
        rejected = request_refund(other, other_order.items.get())
        decide_refund(rejected, self.sales, approve=False)
        response = self.client.get("/api/sales/refunds/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [rejected.pk, self.refund.pk])
        for state, expected in [("requested", self.refund.pk), ("rejected", rejected.pk)]:
            filtered = self.client.get("/api/sales/refunds/", {"status": state})
            self.assertEqual(filtered.status_code, 200)
            self.assertEqual([row["id"] for row in filtered.data], [expected])
        self.assertEqual(self.client.get("/api/sales/refunds/", {"status": "approved"}).data, [])
        detail = self.client.get(self.base)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["customerId"], self.customer.pk)
        self.assertEqual(detail.data["customerName"], self.customer.name)
        self.assertEqual(detail.data["customerEmail"], self.customer.email)
        self.assertEqual(detail.data["orderId"], self.order.pk)
        self.assertEqual(detail.data["productId"], self.product.pk)
        self.assertEqual(detail.data["quantity"], 2)
        self.assertEqual(detail.data["unitPrice"], "1000.00")
        self.assertEqual(detail.data["amount"], "2000.00")
        self.assertIsNone(detail.data["receivedAt"])
        self.assertIsNone(detail.data["receivedBy"])
        self.assertIsNone(detail.data["decidedBy"])

    def test_invalid_filter_returns_400(self):
        self.assertEqual(self.client.get("/api/sales/refunds/", {"status": "unknown"}).status_code, 400)

    def test_missing_refund_returns_404(self):
        url = f"/api/sales/refunds/{self.refund.pk + 1000}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url + "receive/").status_code, 404)
        self.assertEqual(self.client.post(url + "decision/", {"approve": True}, format="json").status_code, 404)

    def test_receipt_is_idempotent_and_does_not_restock(self):
        response = self.client.post(self.base + "receive/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["receivedAt"])
        self.assertEqual(response.data["receivedBy"], self.sales.pk)
        first_received_at = response.data["receivedAt"]
        self.client.force_authenticate(make_user("sales_manager"))
        repeated = self.client.post(self.base + "receive/")
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.data["receivedAt"], first_received_at)
        self.assertEqual(repeated.data["receivedBy"], self.sales.pk)
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)
        self.assertEqual(repeated.data["status"], RefundStatus.REQUESTED)
        self.assertEqual(len(mail.outbox), 0)

    def test_approval_requires_receipt_even_with_client_supplied_timestamp(self):
        response = self.client.post(self.base + "decision/", {
            "approve": True, "receivedAt": timezone.now().isoformat(), "receivedBy": self.sales.pk,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.refund.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.refund.status, RefundStatus.REQUESTED)
        self.assertIsNone(self.refund.decided_at)
        self.assertIsNone(self.refund.decided_by)
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(len(mail.outbox), 0)

    def test_approval_records_decision_once(self):
        self.client.post(self.base + "receive/")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.base + "decision/", {"approve": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], RefundStatus.APPROVED)
        self.assertEqual(response.data["paymentRefund"]["amount"], "2000.00")
        self.assertTrue(response.data["paymentRefund"]["transactionId"].startswith("RFND-"))
        self.assertEqual(response.data["decidedBy"], self.sales.pk)
        self.assertIsNotNone(response.data["decidedAt"])
        for approve in (True, False):
            repeated = self.client.post(self.base + "decision/", {"approve": approve}, format="json")
            self.assertEqual(repeated.status_code, 400)
        self.assertEqual(self.client.post(self.base + "receive/").status_code, 400)
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.order.status, OrderStatus.REFUNDED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("2000.00", mail.outbox[0].body)

    def test_rejection_does_not_require_receipt_or_change_stock(self):
        response = self.client.post(self.base + "decision/", {"approve": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], RefundStatus.REJECTED)
        self.assertEqual(response.data["decidedBy"], self.sales.pk)
        self.assertIsNotNone(response.data["decidedAt"])
        self.assertIsNone(response.data["receivedAt"])
        self.assertEqual(self.client.post(self.base + "receive/").status_code, 400)
        self.assertEqual(self.client.post(self.base + "decision/", {"approve": True}, format="json").status_code, 400)
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)
        self.assertEqual(len(mail.outbox), 0)

    def test_reject_after_receipt_preserves_receipt_record(self):
        self.client.post(self.base + "receive/")
        response = self.client.post(self.base + "decision/", {"approve": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["receivedAt"])
        self.assertEqual(response.data["receivedBy"], self.sales.pk)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_invalid_decision_payload_cannot_mutate_request(self):
        self.client.post(self.base + "receive/")
        for payload in ({}, {"approve": None}, {"approve": "maybe"}, {"status": "approved"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post(self.base + "decision/", payload, format="json").status_code, 400)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, RefundStatus.REQUESTED)

    def test_approval_uses_current_order_status(self):
        self.client.post(self.base + "receive/")
        Order.objects.filter(pk=self.order.pk).update(status=OrderStatus.CANCELLED)
        response = self.client.post(self.base + "decision/", {"approve": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, RefundStatus.REQUESTED)

    def test_return_after_window_ends_can_still_be_decided(self):
        Order.objects.filter(pk=self.order.pk).update(created_at=timezone.now() - timedelta(days=40))
        self.client.post(self.base + "receive/")
        response = self.client.post(self.base + "decision/", {"approve": True}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_partial_approval_keeps_order_delivered_until_all_lines_approved(self):
        customer = make_user()
        cart = Cart.objects.create(user=customer)
        second = make_product(stock=5)
        add_to_cart(cart, self.product, 2)
        add_to_cart(cart, second)
        self.order = paid_order(customer, cart)
        advance_status(self.order)
        advance_status(self.order)
        self.refund = request_refund(customer, self.order.items.get(product=self.product))
        second_item = self.order.items.get(product=second)
        second_refund = request_refund(customer, second_item)
        receive_return(self.refund, self.sales)
        decide_refund(self.refund, self.sales, approve=True)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)
        second.refresh_from_db()
        self.assertEqual(second.stock, 4)
        receive_return(second_refund, self.sales)
        decide_refund(second_refund, self.sales, approve=True)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.REFUNDED)

    def test_service_permissions_cannot_be_bypassed(self):
        for role in ("customer", "product_manager", "support_agent"):
            user = make_user(role)
            with self.subTest(role=role):
                with self.assertRaises(PermissionDenied):
                    receive_return(self.refund, user)
                with self.assertRaises(PermissionDenied):
                    decide_refund(self.refund, user, approve=True)

    def test_direct_service_approval_also_requires_receipt(self):
        with self.assertRaises(ValidationError):
            decide_refund(self.refund, self.sales, approve=True)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, RefundStatus.REQUESTED)


class RefundConcurrencyTests(TransactionTestCase):
    def test_concurrent_line_approvals_finish_order_and_restock_once(self):
        customer, manager = make_user(), make_user("sales_manager")
        products = [make_product(stock=5), make_product(stock=5)]
        cart = Cart.objects.create(user=customer)
        for product in products:
            add_to_cart(cart, product)
        order = paid_order(customer, cart)
        advance_status(order)
        advance_status(order)
        refunds = [request_refund(customer, item) for item in order.items.all()]
        for refund in refunds:
            receive_return(refund, manager)
        barrier = threading.Barrier(2)
        results = []

        def approve(refund):
            try:
                barrier.wait(timeout=10)
                decide_refund(refund, manager, approve=True)
                results.append("approved")
            except Exception as exc:
                results.append(type(exc).__name__)
            finally:
                connection.close()

        threads = [threading.Thread(target=approve, args=(refund,)) for refund in refunds]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(results, ["approved", "approved"])
        self.assertEqual(PaymentRefund.objects.filter(payment=order.payment).count(), 2)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.REFUNDED)
        for product in products:
            product.refresh_from_db()
            self.assertEqual(product.stock, 5)
            self.assertEqual(product.popularity, 0)


    def test_concurrent_approval_of_same_request_calls_bank_once(self):
        from payments import bank
        customer, manager = make_user(), make_user("sales_manager")
        product = make_product(stock=5)
        order = delivered_order(customer, product)
        refund = request_refund(customer, order.items.get())
        receive_return(refund, manager)
        barrier = threading.Barrier(2)
        results = []

        def approve():
            try:
                barrier.wait(timeout=10)
                decide_refund(refund, manager, approve=True)
                results.append("approved")
            except ValidationError:
                results.append("already decided")
            except Exception as exc:
                results.append(type(exc).__name__)
            finally:
                connection.close()

        with patch("payments.services.bank.refund", wraps=bank.refund) as mocked:
            threads = [threading.Thread(target=approve) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=15)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(mocked.call_count, 1)
        self.assertCountEqual(results, ["approved", "already decided"])
        self.assertEqual(PaymentRefund.objects.filter(refund_request=refund).count(), 1)
        product.refresh_from_db()
        self.assertEqual(product.stock, 5)


class RefundPaymentTests(APITestCase):
    def setUp(self):
        self.customer, self.manager = make_user(), make_user("sales_manager")
        self.product = make_product(stock=5)
        self.order = delivered_order(self.customer, self.product, 2)
        self.refund = request_refund(self.customer, self.order.items.get())
        receive_return(self.refund, self.manager)
        self.client.force_authenticate(self.manager)
        self.url = f"/api/sales/refunds/{self.refund.pk}/decision/"

    def assert_pending_without_payment(self):
        self.refund.refresh_from_db()
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.refund.status, RefundStatus.REQUESTED)
        self.assertIsNone(self.refund.decided_at)
        self.assertIsNone(self.refund.decided_by)
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.product.popularity, 2)
        self.assertFalse(PaymentRefund.objects.filter(refund_request=self.refund).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_bank_receives_original_payment_and_frozen_amount(self):
        from payments import bank
        with patch("payments.services.bank.refund", wraps=bank.refund) as mocked:
            response = self.client.post(self.url, {"approve": True, "amount": "1.00"}, format="json")
        self.assertEqual(response.status_code, 200)
        mocked.assert_called_once_with(
            self.order.payment.transaction_id, self.refund.amount,
            idempotency_key=f"refund-request-{self.refund.pk}",
        )
        record = PaymentRefund.objects.get(refund_request=self.refund)
        self.assertEqual(record.payment, self.order.payment)
        self.assertEqual(record.amount, 2000)
        self.assertEqual(response.data["paymentRefund"]["transactionId"], record.transaction_id)
        self.client.force_authenticate(self.customer)
        item = self.client.get(f"/api/orders/{self.order.pk}/").data["items"][0]
        self.assertEqual(item["refund"]["paymentRefund"]["amount"], "2000.00")

    def test_bank_failure_rolls_back_and_can_be_retried(self):
        from payments.bank import RefundDeclined
        with patch("payments.services.bank.refund", side_effect=RefundDeclined("Bank unavailable")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.url, {"approve": True}, format="json")
        self.assertEqual(response.status_code, 502)
        self.assert_pending_without_payment()
        response = self.client.post(self.url, {"approve": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentRefund.objects.count(), 1)

    def test_missing_payment_cannot_be_approved_but_can_be_rejected(self):
        self.order.payment.delete()
        with patch("payments.services.bank.refund") as mocked:
            response = self.client.post(self.url, {"approve": True}, format="json")
        self.assertEqual(response.status_code, 400)
        mocked.assert_not_called()
        self.assert_pending_without_payment()
        self.assertEqual(self.client.post(self.url, {"approve": False}, format="json").status_code, 200)

    def test_refund_cannot_exceed_original_payment(self):
        payment = self.order.payment
        payment.amount = 1000
        payment.save(update_fields=["amount"])
        with patch("payments.services.bank.refund") as mocked:
            response = self.client.post(self.url, {"approve": True}, format="json")
        self.assertEqual(response.status_code, 400)
        mocked.assert_not_called()
        self.assert_pending_without_payment()

    def test_rejection_never_calls_bank(self):
        with patch("payments.services.bank.refund") as mocked:
            self.assertEqual(self.client.post(self.url, {"approve": False}, format="json").status_code, 200)
        mocked.assert_not_called()
        self.assertFalse(PaymentRefund.objects.exists())

    def test_repeated_approval_does_not_call_bank_or_restock_twice(self):
        from payments import bank
        with patch("payments.services.bank.refund", wraps=bank.refund) as mocked:
            self.assertEqual(self.client.post(self.url, {"approve": True}, format="json").status_code, 200)
            self.assertEqual(self.client.post(self.url, {"approve": True}, format="json").status_code, 400)
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(PaymentRefund.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_payment_service_returns_existing_confirmation_without_bank_call(self):
        from payments.services import refund_payment
        decide_refund(self.refund, self.manager, approve=True)
        with patch("payments.services.bank.refund") as mocked:
            record = refund_payment(self.refund)
        mocked.assert_not_called()
        self.assertEqual(record.pk, PaymentRefund.objects.get().pk)

    def test_deleted_saved_card_does_not_prevent_refund(self):
        self.order.payment.card.delete()
        response = self.client.post(self.url, {"approve": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentRefund.objects.get().payment_id, self.order.payment.pk)

    def test_database_failure_after_bank_confirmation_is_safe_to_retry(self):
        from django.db import IntegrityError
        from payments import bank
        with patch("payments.services.bank.refund", wraps=bank.refund) as mocked:
            with patch("payments.services.PaymentRefund.objects.create", side_effect=IntegrityError("write failed")):
                with self.assertRaises(IntegrityError):
                    decide_refund(self.refund, self.manager, approve=True)
            self.assert_pending_without_payment()
            decide_refund(self.refund, self.manager, approve=True)
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(mocked.call_args_list[0], mocked.call_args_list[1])
        record = PaymentRefund.objects.get()
        self.assertEqual(record.transaction_id, bank.refund(
            self.order.payment.transaction_id, self.refund.amount,
            idempotency_key=f"refund-request-{self.refund.pk}",
        ))

    def test_discounted_payment_is_refunded_after_campaign_ends(self):
        user = make_user()
        product = make_product(price="1000.00")
        product.apply_discount(30)
        order = delivered_order(user, product)
        product.apply_discount(0)
        refund = request_refund(user, order.items.get())
        receive_return(refund, self.manager)
        decide_refund(refund, self.manager, approve=True)
        self.assertEqual(PaymentRefund.objects.get(refund_request=refund).amount, 700)

    def test_partial_refunds_cannot_cumulatively_exceed_payment(self):
        user = make_user()
        cart = Cart.objects.create(user=user)
        products = [make_product(), make_product()]
        for product in products:
            add_to_cart(cart, product)
        order = paid_order(user, cart)
        advance_status(order)
        advance_status(order)
        first, second = [request_refund(user, item) for item in order.items.all()]
        for refund in (first, second):
            receive_return(refund, self.manager)
        decide_refund(first, self.manager, approve=True)
        payment = order.payment
        payment.amount = 1500
        payment.save(update_fields=["amount"])
        with self.assertRaises(ValidationError):
            decide_refund(second, self.manager, approve=True)
        self.assertEqual(payment.refunds.count(), 1)
        second.refresh_from_db()
        self.assertEqual(second.status, RefundStatus.REQUESTED)

    def test_zero_price_purchase_has_zero_refund_confirmation(self):
        user = make_user()
        product = make_product()
        product.apply_discount(100)
        order = delivered_order(user, product)
        refund = request_refund(user, order.items.get())
        receive_return(refund, self.manager)
        decide_refund(refund, self.manager, approve=True)
        self.assertEqual(PaymentRefund.objects.get(refund_request=refund).amount, 0)

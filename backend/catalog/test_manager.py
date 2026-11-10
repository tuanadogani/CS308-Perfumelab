from django.test import TestCase
from rest_framework.test import APIClient
from catalog.factories import make_product, make_user
from catalog.models import Category, Product
from orders.models import Order, OrderItem, Delivery
from reviews.models import Comment

BASE = '/api/product-manager/'


class ProductManagerAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = make_user('product_manager')
        self.customer = make_user()
        self.product = make_product()
        self.client.force_authenticate(self.manager)

    def test_every_endpoint_is_role_protected(self):
        endpoints = ['products/', f'products/{self.product.pk}/', 'categories/',
                     f'categories/{self.product.category_id}/', 'deliveries/', 'comments/']
        for role in ['customer', 'sales_manager', 'support_agent']:
            self.client.force_authenticate(make_user(role))
            for endpoint in endpoints:
                self.assertEqual(self.client.get(BASE + endpoint).status_code, 403)
            self.assertEqual(self.client.patch(BASE + 'orders/1/status/', {'status': 'delivered'}, format='json').status_code, 403)
            self.assertEqual(self.client.patch(BASE + 'comments/1/', {'approve': True}, format='json').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(BASE + 'products/').status_code, 401)

    def test_create_update_stock_and_soft_delete(self):
        payload = dict(name='New scent', model='N1', serial_number='UNIQUE-NEW', description='Fresh',
                       brand='New brand', category=self.product.category.slug, gender='Unisex',
                       volume_ml=50, stock=3, warranty_status='2 years', distributor='Distributor',
                       families=['Fresh'], notes={'top': ['Lemon']})
        response = self.client.post(BASE + 'products/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data['id']
        product = Product.objects.get(pk=pk)
        self.assertEqual(product.notes.get().name, 'Lemon')
        self.assertEqual(product.families.get().name, 'Fresh')
        url = BASE + f'products/{pk}/'
        self.assertEqual(self.client.patch(url, {'stock': -1}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'stock': 7, 'price': 999}, format='json').status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.stock, 7)
        self.assertEqual(product.price, 0)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(f'/api/products/{pk}/').status_code, 404)
        self.assertTrue(Product.objects.filter(pk=pk, active=False).exists())
        self.assertEqual(self.client.patch(url, {'active': True}, format='json').status_code, 200)

    def test_category_deletion_protects_existing_products(self):
        self.assertEqual(self.client.delete(BASE + f'categories/{self.product.category_id}/').status_code, 400)
        response = self.client.post(BASE + 'categories/', {'name': 'Cologne', 'slug': 'cologne'}, format='json')
        self.assertEqual(response.status_code, 201)
        pk = response.data['id']
        self.assertEqual(self.client.patch(BASE + f'categories/{pk}/', {'name': 'New Cologne'}, format='json').status_code, 200)
        self.assertEqual(self.client.delete(BASE + f'categories/{pk}/').status_code, 204)
        self.assertFalse(Category.objects.filter(pk=pk).exists())

    def test_delivery_transitions_and_completion(self):
        order = Order.objects.create(user=self.customer, shipping_address='Original address', total=100)
        item = OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=100, unit_cost=50)
        delivery = Delivery.objects.create(order_item=item, delivery_address='Original address')
        response = self.client.get(BASE + 'deliveries/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['customerId'], self.customer.pk)
        self.assertEqual(response.data[0]['address'], 'Original address')
        url = BASE + f'orders/{order.pk}/status/'
        self.assertEqual(self.client.patch(url, {'status': 'delivered'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'status': 'in_transit'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'status': 'in_transit'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'status': 'delivered'}, format='json').status_code, 200)
        delivery.refresh_from_db(); order.refresh_from_db()
        self.assertTrue(delivery.completed)
        self.assertIsNotNone(order.delivered_at)
        self.assertEqual(self.client.patch(url, {'status': 'processing'}, format='json').status_code, 400)

    def test_moderation_requires_explicit_decision(self):
        comment = Comment.objects.create(user=self.customer, product=self.product, text='Excellent')
        self.assertEqual(self.client.get(BASE + 'comments/').data[0]['id'], comment.pk)
        url = BASE + f'comments/{comment.pk}/'
        self.assertEqual(self.client.patch(url, {}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'approve': True}, format='json').status_code, 200)
        comment.refresh_from_db()
        self.assertTrue(comment.approved)
        self.assertEqual(comment.reviewed_by_id, self.manager.pk)
        self.assertIsNotNone(comment.reviewed_at)
        self.assertEqual(self.client.patch(url, {'approve': False}, format='json').status_code, 200)
        comment.refresh_from_db()
        self.assertFalse(comment.approved)

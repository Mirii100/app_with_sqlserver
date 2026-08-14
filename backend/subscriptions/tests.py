from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from transactions.models import Transaction

from .models import Subscription, SubscriptionWallet, UserSubscription

User = get_user_model()


class SubscriptionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        self.subscription = Subscription.objects.create(
            name='TestStream',
            description='Streaming movies and series',
            price='1100.00',
            billing_cycle='monthly',
        )
        self.client.force_authenticate(user=self.user)

    def test_available_lists_seeded_products(self):
        response = self.client.get('/api/subscriptions/available/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(s['name'] == 'Netflix' for s in data))

    def test_available_excludes_inactive_products(self):
        self.subscription.active = False
        self.subscription.save()
        response = self.client.get('/api/subscriptions/available/')
        names = [s['name'] for s in response.json()]
        self.assertNotIn('TestStream', names)

    def test_create_subscription(self):
        response = self.client.post('/api/subscriptions/', {
            'user': self.user.id,
            'subscription': self.subscription.id,
        })
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['price'], '1100.00')
        self.assertEqual(data['name'], 'TestStream')

    def test_create_is_idempotent(self):
        UserSubscription.objects.create(
            user=self.user,
            subscription=self.subscription,
        )
        response = self.client.post('/api/subscriptions/', {
            'user': self.user.id,
            'subscription': self.subscription.id,
        })
        self.assertEqual(response.status_code, 200)

    def test_create_rejects_missing_fields(self):
        response = self.client.post('/api/subscriptions/', {'user': self.user.id})
        self.assertEqual(response.status_code, 400)

    def test_create_rejects_unknown_subscription(self):
        response = self.client.post('/api/subscriptions/', {
            'user': self.user.id,
            'subscription': 99999,
        })
        self.assertEqual(response.status_code, 404)

    def test_list_user_subscriptions(self):
        UserSubscription.objects.create(
            user=self.user,
            subscription=self.subscription,
        )
        response = self.client.get(f'/api/subscriptions/?user={self.user.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'TestStream')

    def test_cancel_subscription(self):
        UserSubscription.objects.create(
            user=self.user,
            subscription=self.subscription,
        )
        response = self.client.delete(
            f'/api/subscriptions/?user={self.user.id}&subscription={self.subscription.id}'
        )
        self.assertEqual(response.status_code, 200)
        obj = UserSubscription.objects.get(user=self.user, subscription=self.subscription)
        self.assertEqual(obj.status, 'cancelled')

    def test_cancel_inactive_subscription_returns_404(self):
        response = self.client.delete(
            f'/api/subscriptions/?user={self.user.id}&subscription={self.subscription.id}'
        )
        self.assertEqual(response.status_code, 404)


class SubscriptionWalletAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='walletuser',
            email='wallet@example.com',
            password='testpass123',
            balance='5000.00',
        )
        self.client.force_authenticate(user=self.user)

    def test_get_creates_wallet_with_12_digit_account_number(self):
        response = self.client.get(f'/api/subscription-wallet/?user={self.user.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['balance'], '0.00')
        self.assertEqual(data['currency'], 'KSh')
        self.assertEqual(len(data['account_number']), 12)
        self.assertNotEqual(data['account_number'][0], '0')

    def test_get_is_idempotent(self):
        self.client.get(f'/api/subscription-wallet/?user={self.user.id}')
        second = self.client.get(f'/api/subscription-wallet/?user={self.user.id}')
        self.assertEqual(second.json()['account_number'],
                         SubscriptionWallet.objects.get(user=self.user).account_number)

    def test_fund_deducts_from_account_balance(self):
        response = self.client.post('/api/subscription-wallet/', {
            'user': self.user.id,
            'amount': '1100.00',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['wallet_balance'], '1100.00')
        self.assertEqual(data['new_balance'], '3900.00')

        self.user.refresh_from_db()
        self.assertEqual(float(self.user.balance), 3900.00)
        wallet = SubscriptionWallet.objects.get(user=self.user)
        self.assertEqual(float(wallet.balance), 1100.00)

    def test_fund_creates_transaction(self):
        self.client.post('/api/subscription-wallet/', {
            'user': self.user.id,
            'amount': '500.00',
        })
        txn = Transaction.objects.get(user=self.user)
        self.assertEqual(txn.category, 'subscription_wallet_funding')
        self.assertEqual(txn.type, 'withdrawal')
        self.assertEqual(float(txn.amount), 500.00)

    def test_fund_rejects_insufficient_balance(self):
        response = self.client.post('/api/subscription-wallet/', {
            'user': self.user.id,
            'amount': '99999.00',
        })
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(float(self.user.balance), 5000.00)

    def test_fund_rejects_zero_or_negative(self):
        for amount in ['0', '-5']:
            response = self.client.post('/api/subscription-wallet/', {
                'user': self.user.id,
                'amount': amount,
            })
            self.assertEqual(response.status_code, 400)

    def test_fund_rejects_invalid_amount(self):
        response = self.client.post('/api/subscription-wallet/', {
            'user': self.user.id,
            'amount': 'abc',
        })
        self.assertEqual(response.status_code, 400)
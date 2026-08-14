from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cpuser',
            email='cpuser@example.com',
            password='oldpass123',
            phone_number='+254700111222',
            balance='0',
        )
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_change_password_success(self):
        response = self.client.post('/api/auth/change-password/', {
            'user_id': self.user.id,
            'new_password': 'newpass456',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))

    def test_change_password_requires_auth(self):
        anonymous = APIClient()
        response = anonymous.post('/api/auth/change-password/', {
            'user_id': self.user.id,
            'new_password': 'newpass456',
        }, format='json')
        self.assertEqual(response.status_code, 401)

    def test_change_password_forbidden_for_other_user(self):
        other = User.objects.create_user(
            username='cpother',
            email='cpother@example.com',
            password='oldpass123',
            phone_number='+254700111223',
            balance='0',
        )
        response = self.client.post('/api/auth/change-password/', {
            'user_id': other.id,
            'new_password': 'newpass456',
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_change_password_rejects_short_password(self):
        response = self.client.post('/api/auth/change-password/', {
            'user_id': self.user.id,
            'new_password': 'abc',
        }, format='json')
        self.assertEqual(response.status_code, 400)

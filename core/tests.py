from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class LoginFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_root_and_login_routes_render_login_page(self):
        self.assertContains(self.client.get('/'), 'Cooking gas at your door.')
        self.assertContains(self.client.get('/login/'), 'Choose account type')

    def test_customer_registration_creates_a_password_account_and_logs_in(self):
        credentials = {
            'first_name': 'Sam',
            'last_name': 'Example',
            'email': 'not-an-email',
            'password': 'Strong-Password-938!',
            'password_confirm': 'Strong-Password-938!',
        }
        response = self.client.post('/api/auth/register', credentials, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('valid email', response.data['detail'])
        credentials['email'] = 'sam@example.org'
        response = self.client.post('/api/auth/register', credentials, format='json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='sam@example.org')
        self.assertEqual(user.first_name, 'Sam')
        self.assertEqual(user.role, User.ROLE_CUSTOMER)
        self.assertEqual(response.data['redirect'], '/app/')
        self.assertEqual(self.client.get('/api/me').data['email'], 'sam@example.org')

    def test_registered_roles_sign_in_with_email_and_password(self):
        accounts = [
            ('customer@example.org', User.ROLE_CUSTOMER, '/app/'),
            ('rider@example.org', User.ROLE_RIDER, '/rider/'),
            ('vendor@example.org', User.ROLE_VENDOR, '/vendor/'),
        ]
        for index, (email, role, destination) in enumerate(accounts):
            User.objects.create_user(
                username=f'account-{index}',
                email=email,
                password='Strong-Password-938!',
                role=role,
            )
            response = self.client.post(
                '/api/auth/login',
                {'email': email, 'password': 'Strong-Password-938!', 'role': role},
                format='json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['redirect'], destination)

    def test_account_cannot_sign_in_under_another_role(self):
        User.objects.create_user(
            username='customer-one',
            email='customer@example.org',
            password='Strong-Password-938!',
            phone='+256700000001',
            role=User.ROLE_CUSTOMER,
        )
        response = self.client.post(
            '/api/auth/login',
            {
                'email': 'customer@example.org',
                'password': 'Strong-Password-938!',
                'role': User.ROLE_VENDOR,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('customer, not a vendor', response.data['detail'])

    def test_invalid_credentials_are_rejected(self):
        User.objects.create_user(
            username='customer-one',
            email='customer@example.org',
            password='Strong-Password-938!',
            role=User.ROLE_CUSTOMER,
        )
        response = self.client.post(
            '/api/auth/login',
            {'email': 'customer@example.org', 'password': 'incorrect', 'role': User.ROLE_CUSTOMER},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['detail'], 'Email or password is incorrect.')

    def test_unregistered_rider_and_vendor_are_referred_to_support(self):
        for role in (User.ROLE_RIDER, User.ROLE_VENDOR):
            response = self.client.post(
                '/api/auth/login',
                {'email': 'unregistered@example.org', 'password': 'anything', 'role': role},
                format='json',
            )
            self.assertEqual(response.status_code, 403)
            self.assertIn(f'not registered as a {role}', response.data['detail'])
            self.assertIn('Contact QuickRefill support.', response.data['detail'])

    def test_registration_rejects_duplicate_email_and_password_mismatch(self):
        User.objects.create_user(
            username='existing',
            email='existing@example.org',
            password='Strong-Password-938!',
            role=User.ROLE_CUSTOMER,
        )
        payload = {
            'first_name': 'New',
            'email': 'existing@example.org',
            'password': 'Strong-Password-938!',
            'password_confirm': 'different',
        }
        duplicate = self.client.post('/api/auth/register', payload, format='json')
        self.assertEqual(duplicate.status_code, 409)
        payload['email'] = 'new@example.org'
        mismatch = self.client.post('/api/auth/register', payload, format='json')
        self.assertEqual(mismatch.status_code, 400)
        self.assertIn('do not match', mismatch.data['detail'])

    def test_protected_pages_redirect_and_removed_demo_route_is_not_found(self):
        for path in ('/app/', '/rider/', '/vendor/'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/login/')
        self.assertEqual(self.client.get('/demo/').status_code, 404)

    def test_signup_only_creates_customer_accounts(self):
        response = self.client.post(
            '/api/auth/register',
            {
                'first_name': 'New',
                'email': 'new@example.org',
                'password': 'Strong-Password-938!',
                'password_confirm': 'Strong-Password-938!',
                'role': User.ROLE_VENDOR,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(email='new@example.org').role, User.ROLE_CUSTOMER)

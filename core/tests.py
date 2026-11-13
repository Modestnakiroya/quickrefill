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


class TrackingFixture(TestCase):
    PW = 'Strong-Password-938!'

    def setUp(self):
        from .models import Order, Rider, StockItem, Vendor
        self.customer = User.objects.create_user(username='c', email='c@x.org', password=self.PW, role=User.ROLE_CUSTOMER)
        self.other = User.objects.create_user(username='o', email='o@x.org', password=self.PW, role=User.ROLE_CUSTOMER)
        ru = User.objects.create_user(username='r', email='r@x.org', password=self.PW, role=User.ROLE_RIDER)
        vu = User.objects.create_user(username='v', email='v@x.org', password=self.PW, role=User.ROLE_VENDOR)
        self.rider = Rider.objects.create(user=ru)
        vendor = Vendor.objects.create(owner=vu, name='V', location='Loc', lat=0.335, lng=32.567)
        stock = StockItem.objects.create(vendor=vendor, brand='Stabex', size_kg=6, price_refill=60000,
                                         price_exchange=145000, quantity=5)
        self.order = Order.objects.create(
            code='QR-T1', customer=self.customer, vendor=vendor, stock_item=stock, rider=self.rider,
            delivery_address='x', lat=0.30, lng=32.60, payment_method='cash',
            gas_price=60000, delivery_fee=5000, total=65000, rider_fee=4000,
            status=Order.STATUS_ON_THE_WAY,
        )
        self.url = f'/api/orders/{self.order.id}/track'

    def _client(self, email, role):
        c = APIClient()
        r = c.post('/api/auth/login', {'email': email, 'password': self.PW, 'role': role}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return c


class LiveTrackingTests(TrackingFixture):
    def test_rider_location_is_stored_and_shown_live_to_customer(self):
        rc = self._client('r@x.org', 'rider')
        self.assertEqual(rc.post('/api/rider/location', {'lat': 0.31, 'lng': 32.59}, format='json').status_code, 200)
        t = self._client('c@x.org', 'customer').get(self.url).data
        self.assertTrue(t['live'])
        self.assertAlmostEqual(t['rider_lat'], 0.31)
        self.assertAlmostEqual(t['rider_lng'], 32.59)
        self.assertGreaterEqual(t['eta_minutes'], 1)

    def test_eta_shrinks_as_rider_gets_closer(self):
        rc, cc = self._client('r@x.org', 'rider'), self._client('c@x.org', 'customer')
        rc.post('/api/rider/location', {'lat': 0.335, 'lng': 32.567}, format='json')
        far = cc.get(self.url).data['eta_minutes']
        rc.post('/api/rider/location', {'lat': 0.3005, 'lng': 32.5995}, format='json')
        near = cc.get(self.url).data['eta_minutes']
        self.assertLess(near, far)

    def test_stale_gps_falls_back_to_estimated_position(self):
        from datetime import timedelta
        from django.utils import timezone
        self.rider.lat, self.rider.lng = 1.0, 1.0
        self.rider.location_updated_at = timezone.now() - timedelta(minutes=5)
        self.rider.save()
        self.order.on_the_way_at = timezone.now()
        self.order.save()
        t = self._client('c@x.org', 'customer').get(self.url).data
        self.assertFalse(t['live'])
        self.assertNotEqual(t['rider_lat'], 1.0)

    def test_tracking_is_limited_to_the_orders_own_people(self):
        self.assertEqual(self._client('o@x.org', 'customer').get(self.url).status_code, 403)
        self.assertEqual(self._client('c@x.org', 'customer').get(self.url).status_code, 200)
        self.assertEqual(self._client('v@x.org', 'vendor').get(self.url).status_code, 200)
        self.assertEqual(self._client('r@x.org', 'rider').get(self.url).status_code, 200)

    def test_location_endpoint_validation(self):
        rc = self._client('r@x.org', 'rider')
        self.assertEqual(rc.post('/api/rider/location', {'lat': 'abc', 'lng': 1}, format='json').status_code, 400)
        self.assertEqual(rc.post('/api/rider/location', {'lat': 95, 'lng': 1}, format='json').status_code, 400)
        self.assertEqual(self._client('c@x.org', 'customer').post(
            '/api/rider/location', {'lat': 1, 'lng': 1}, format='json').status_code, 403)


class RiderPoolAndOrderFlowTests(TrackingFixture):

    def setUp(self):
        super().setUp()
        from .models import Order, Rider
        self.order.rider = None
        self.order.status = Order.STATUS_NEW
        self.order.save()
        ru2 = User.objects.create_user(username='r2', email='r2@x.org', password=self.PW, role=User.ROLE_RIDER)
        self.rider2 = Rider.objects.create(user=ru2)
        for r in (self.rider, self.rider2):
            r.online = True
            r.save()

    def test_vendor_accept_puts_order_in_pool_without_auto_assigning(self):
        from .models import Order
        self._client('v@x.org', 'vendor').post(f'/api/vendor/orders/{self.order.id}/accept')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_ACCEPTED)
        self.assertIsNone(self.order.rider)
        # Both online riders see it as an offer.
        for email in ('r@x.org', 'r2@x.org'):
            data = self._client(email, 'rider').get('/api/rider/jobs/available').data
            self.assertEqual(data['mode'], 'offer')
            self.assertEqual(data['job']['id'], self.order.id)

    def test_first_rider_wins_second_gets_409(self):
        from .models import Order
        self._client('v@x.org', 'vendor').post(f'/api/vendor/orders/{self.order.id}/accept')
        r1, r2 = self._client('r@x.org', 'rider'), self._client('r2@x.org', 'rider')
        self.assertEqual(r1.post(f'/api/rider/jobs/{self.order.id}/accept').status_code, 200)
        self.assertEqual(r2.post(f'/api/rider/jobs/{self.order.id}/accept').status_code, 409)
        self.order.refresh_from_db()
        self.assertEqual(self.order.rider_id, self.rider.id)
        self.assertEqual(self.order.status, Order.STATUS_RIDER_ASSIGNED)
        self.assertEqual(r2.get('/api/rider/jobs/available').data['mode'], 'idle')
        self.assertEqual(r1.get('/api/rider/jobs/available').data['mode'], 'active')

    def test_offline_rider_gets_no_offer_and_cannot_accept(self):
        self._client('v@x.org', 'vendor').post(f'/api/vendor/orders/{self.order.id}/accept')
        self.rider.online = False
        self.rider.save()
        rc = self._client('r@x.org', 'rider')
        self.assertEqual(rc.get('/api/rider/jobs/available').data['mode'], 'offline')
        self.assertEqual(rc.post(f'/api/rider/jobs/{self.order.id}/accept').status_code, 400)

    def test_declined_job_is_hidden_only_for_that_rider(self):
        self._client('v@x.org', 'vendor').post(f'/api/vendor/orders/{self.order.id}/accept')
        r1, r2 = self._client('r@x.org', 'rider'), self._client('r2@x.org', 'rider')
        r1.post(f'/api/rider/jobs/{self.order.id}/decline')
        self.assertEqual(r1.get('/api/rider/jobs/available').data['mode'], 'idle')
        self.assertEqual(r2.get('/api/rider/jobs/available').data['mode'], 'offer')

    def test_order_detail_permissions(self):
        url = f'/api/orders/{self.order.id}'
        self.assertEqual(self._client('c@x.org', 'customer').get(url).status_code, 200)
        self.assertEqual(self._client('o@x.org', 'customer').get(url).status_code, 403)
        # Unclaimed + not yet accepted: riders must not see it.
        self.assertEqual(self._client('r@x.org', 'rider').get(url).status_code, 403)

    def test_orders_list_reports_whether_delivered_order_is_rated(self):
        from .models import Order, Rating
        self.order.status = Order.STATUS_DELIVERED
        self.order.save()
        cc = self._client('c@x.org', 'customer')
        self.assertFalse(cc.get('/api/orders').data[0]['rated'])
        Rating.objects.create(order=self.order, rider_stars=5, vendor_stars=5)
        self.assertTrue(cc.get('/api/orders').data[0]['rated'])

    def test_track_has_no_rider_details_before_assignment(self):
        self.order.status = 'accepted'
        self.order.save()
        t = self._client('c@x.org', 'customer').get(self.url).data
        self.assertIsNone(t['rider_name'])
        self.assertIsNone(t['rider_phone'])
        self.assertFalse(t['seal_checked'])


class FullDeliveryFlowTest(TrackingFixture):
    def test_order_to_delivery_with_live_gps(self):
        from .models import Order
        for r in (self.rider,):
            r.online = True
            r.save()
        self.order.delete()
        cc = self._client('c@x.org', 'customer')
        stock = self.order.stock_item if False else None  # fixture stock is on the deleted order
        from .models import StockItem
        stock = StockItem.objects.first()

        r = cc.post('/api/orders', {
            'stock_item_id': stock.id, 'order_type': 'refill', 'delivery_address': 'Ntinda',
            'lat': 0.3542, 'lng': 32.6122, 'payment_method': 'cash',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        oid = r.data['id']
        track = f'/api/orders/{oid}/track'

        # Customer sees "no rider yet" and no invented phone/position.
        t = cc.get(track).data
        self.assertIsNone(t['rider_name'])
        self.assertIsNone(t['rider_phone'])
        self.assertIsNone(t['rider_lat'])

        vc, rc = self._client('v@x.org', 'vendor'), self._client('r@x.org', 'rider')
        self.assertEqual(vc.post(f'/api/vendor/orders/{oid}/accept').status_code, 200)
        self.assertEqual(rc.get('/api/rider/jobs/available').data['mode'], 'offer')
        self.assertEqual(rc.post(f'/api/rider/jobs/{oid}/accept').status_code, 200)

        # Rider heads to the vendor with live GPS; customer sees it.
        rc.post('/api/rider/location', {'lat': 0.34, 'lng': 32.57}, format='json')
        t = cc.get(track).data
        self.assertTrue(t['live'])
        self.assertEqual(t['status'], Order.STATUS_RIDER_ASSIGNED)
        self.assertAlmostEqual(t['rider_lat'], 0.34)

        for step in ('collected', 'seal_checked', 'handover', 'empty_collected', 'payment'):
            res = rc.post(f'/api/rider/jobs/{oid}/step', {'step': step}, format='json')
            self.assertEqual(res.status_code, 200, (step, res.data))
            rc.post('/api/rider/location', {'lat': 0.35, 'lng': 32.60}, format='json')
            t = cc.get(track).data
            self.assertTrue(t['live'], step)             # collecting must not overwrite real GPS
            self.assertAlmostEqual(t['rider_lat'], 0.35, msg=step)
        self.assertTrue(cc.get(track).data['seal_checked'])

        res = rc.post(f'/api/rider/jobs/{oid}/step', {'step': 'delivered'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        t = cc.get(track).data
        self.assertEqual(t['status'], Order.STATUS_DELIVERED)
        self.assertEqual(t['eta_minutes'], 0)
        self.assertEqual(rc.get('/api/rider/jobs/available').data['mode'], 'idle')

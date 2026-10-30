from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Order, Rider, Settlement, StockItem, User, Vendor


class Command(BaseCommand):
    help = 'Seed QuickRefill data (safe to run repeatedly)'

    def handle(self, *args, **options):
        customer = self._user(
            '700000001', User.ROLE_CUSTOMER, 'Praise', '', 'praise@quickrefill.test'
        )
        rider_user = self._user(
            '700000002', User.ROLE_RIDER, 'Musa', 'Kato', 'musa@quickrefill.test'
        )
        vendor_user = self._user(
            '700000003', User.ROLE_VENDOR, 'Wandegeya', 'Gas Point', 'vendor@quickrefill.test'
        )

        vendor, _ = Vendor.objects.update_or_create(
            owner=vendor_user,
            defaults={
                'name': 'Wandegeya Gas Point',
                'location': 'Wandegeya, Kampala',
                'verified': True,
                'accepting_orders': True,
                'rating': Decimal('4.8'),
                'lat': 0.3350,
                'lng': 32.5670,
            },
        )

        rider, _ = Rider.objects.update_or_create(
            user=rider_user,
            defaults={
                'online': True,
                'rating': Decimal('4.9'),
                'trips_count': 128,
                'vehicle_plate': 'UBE 204Q',
                'lat': 0.3350,
                'lng': 32.5670,
            },
        )

        stock_defs = [
            # brand, size, refill, exchange, qty
            ('Stabex', 6, 60000, 145000, 14),
            ('Stabex', 12, 115000, 280000, 6),
            ('Stabex', 45, 420000, 950000, 0),  # hidden from customers
            ('Oryx', 12, 58000, 275000, 3),
            ('Oryx', 6, 59000, 140000, 8),
            ('Total', 6, 62000, 148000, 2),  # Only 2 left
            ('Total', 12, 118000, 285000, 5),
            ('Shell', 6, 61000, 146000, 0),  # out of stock
            ('Shell', 12, 116000, 282000, 4),
            ('Hashi', 6, 59500, 142000, 9),
            ('Hashi', 45, 410000, 940000, 3),
        ]
        for brand, size, refill, exchange, qty in stock_defs:
            StockItem.objects.update_or_create(
                vendor=vendor,
                brand=brand,
                size_kg=size,
                defaults={
                    'price_refill': refill,
                    'price_exchange': exchange,
                    'quantity': qty,
                    'low_stock_threshold': 2,
                },
            )

        StockItem.objects.filter(vendor=vendor, brand='Oryx', size_kg=12).update(price_refill=58000, quantity=3)
        StockItem.objects.filter(vendor=vendor, brand='Total', size_kg=6).update(price_refill=62000, quantity=2)
        StockItem.objects.filter(vendor=vendor, brand='Shell', size_kg=6).update(price_refill=61000, quantity=0)
        StockItem.objects.filter(vendor=vendor, brand='Stabex', size_kg=6).update(price_refill=60000, quantity=14)
        StockItem.objects.filter(vendor=vendor, brand='Stabex', size_kg=45).update(quantity=0)

        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        sales = 2520000
        commission = 5
        payout = int(sales - sales * commission / 100)
        Settlement.objects.update_or_create(
            vendor=vendor,
            week_start=week_start,
            defaults={
                'gas_sales': sales,
                'commission_percent': Decimal('5.00'),
                'payout': payout,
            },
        )

        # Populate order and performance history for a usable account.
        stabex6 = StockItem.objects.get(vendor=vendor, brand='Stabex', size_kg=6)
        oryx12 = StockItem.objects.get(vendor=vendor, brand='Oryx', size_kg=12)
        total6 = StockItem.objects.get(vendor=vendor, brand='Total', size_kg=6)
        shell12 = StockItem.objects.get(vendor=vendor, brand='Shell', size_kg=12)
        hashi6 = StockItem.objects.get(vendor=vendor, brand='Hashi', size_kg=6)

        samples = [
            {
                'code': 'QR-20411',
                'stock': stabex6,
                'status': Order.STATUS_NEW,
                'order_type': Order.TYPE_REFILL,
                'payment_method': Order.PAY_MOMO,
                'payment_status': Order.PAY_PAID,
                'rider': None,
            },
            {
                'code': 'QR-20412',
                'stock': oryx12,
                'status': Order.STATUS_ACCEPTED,
                'order_type': Order.TYPE_REFILL,
                'payment_method': Order.PAY_AIRTEL,
                'payment_status': Order.PAY_PAID,
                'rider': None,
            },
            {
                'code': 'QR-20413',
                'stock': total6,
                'status': Order.STATUS_DELIVERED,
                'order_type': Order.TYPE_EXCHANGE,
                'payment_method': Order.PAY_CASH,
                'payment_status': Order.PAY_PAID,
                'rider': rider,
            },
            {
                'code': 'QR-20414',
                'stock': shell12,
                'status': Order.STATUS_DELIVERED,
                'order_type': Order.TYPE_REFILL,
                'payment_method': Order.PAY_MOMO,
                'payment_status': Order.PAY_PAID,
                'rider': rider,
            },
            {
                'code': 'QR-20415',
                'stock': hashi6,
                'status': Order.STATUS_ACCEPTED,
                'order_type': Order.TYPE_REFILL,
                'payment_method': Order.PAY_MOMO,
                'payment_status': Order.PAY_PAID,
                'rider': None,
            },
        ]

        now = timezone.now()
        for i, s in enumerate(samples):
            stock = s['stock']
            price = stock.price_refill if s['order_type'] == Order.TYPE_REFILL else stock.price_exchange
            defaults = {
                'customer': customer,
                'vendor': vendor,
                'rider': s['rider'],
                'stock_item': stock,
                'order_type': s['order_type'],
                'delivery_address': 'Garden Courts Hostel, Kikoni',
                'address_note': 'Room B12',
                'lat': 0.3285,
                'lng': 32.5590,
                'schedule': Order.SCHEDULE_ASAP,
                'payment_method': s['payment_method'],
                'payment_status': s['payment_status'],
                'gas_price': price,
                'delivery_fee': 5000,
                'total': price + 5000,
                'status': s['status'],
                'rider_fee': 4000,
                'seal_checked': s['status'] in (Order.STATUS_ON_THE_WAY, Order.STATUS_DELIVERED),
                'handover_confirmed': s['status'] in (Order.STATUS_ON_THE_WAY, Order.STATUS_DELIVERED),
                'empty_collected': s['status'] == Order.STATUS_DELIVERED,
                'accepted_at': now - timedelta(hours=3 - i) if s['status'] != Order.STATUS_NEW else None,
                'rider_assigned_at': now - timedelta(hours=2) if s['rider'] else None,
                'collected_at': now - timedelta(hours=1) if s['status'] in (Order.STATUS_ON_THE_WAY, Order.STATUS_DELIVERED) else None,
                'on_the_way_at': now - timedelta(minutes=20) if s['status'] in (Order.STATUS_ON_THE_WAY, Order.STATUS_DELIVERED) else None,
                'delivered_at': now - timedelta(minutes=5) if s['status'] == Order.STATUS_DELIVERED else None,
            }
            Order.objects.update_or_create(code=s['code'], defaults=defaults)

        self.stdout.write(self.style.SUCCESS('QuickRefill data seeded successfully.'))

    def _user(self, nine, role, first, last, email):
        phone = f'+256{nine}'
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'username': f'user_{nine}',
                'email': email,
                'first_name': first,
                'last_name': last,
                'role': role,
            },
        )
        changed = False
        if user.role != role:
            user.role = role
            changed = True
        if user.first_name != first or user.last_name != last:
            user.first_name = first
            user.last_name = last
            changed = True
        if user.email.endswith('@quickrefill.invalid'):
            user.email = email
            user.set_password('QuickRefill-Local-Access-2026!')
            changed = True
        elif not user.has_usable_password():
            user.set_password('QuickRefill-Local-Access-2026!')
            changed = True
        if changed:
            user.save()
        return user

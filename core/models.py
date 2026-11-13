from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_CUSTOMER = 'customer'
    ROLE_RIDER = 'rider'
    ROLE_VENDOR = 'vendor'
    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_RIDER, 'Rider'),
        (ROLE_VENDOR, 'Vendor'),
    ]

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.phone or "-"})'


class Vendor(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=255)
    verified = models.BooleanField(default=True)
    accepting_orders = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.8)
    lat = models.FloatField(default=0.3350)
    lng = models.FloatField(default=32.5670)

    def __str__(self):
        return self.name


class StockItem(models.Model):
    SIZE_CHOICES = [(6, '6 kg'), (12, '12 kg'), (45, '45 kg')]

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='stock_items')
    brand = models.CharField(max_length=60)
    size_kg = models.IntegerField(choices=SIZE_CHOICES)
    price_refill = models.PositiveIntegerField()
    price_exchange = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=2)

    class Meta:
        unique_together = ('vendor', 'brand', 'size_kg')

    def __str__(self):
        return f'{self.brand} {self.size_kg}kg'

    @property
    def in_stock(self):
        return self.quantity > 0

    @property
    def is_low(self):
        return 0 < self.quantity <= self.low_stock_threshold


class Rider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    online = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.9)
    trips_count = models.PositiveIntegerField(default=0)
    vehicle_plate = models.CharField(max_length=20, default='UBE 204Q')
    lat = models.FloatField(default=0.3350)
    lng = models.FloatField(default=32.5670)
    location_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Order(models.Model):
    TYPE_REFILL = 'refill'
    TYPE_EXCHANGE = 'exchange'
    TYPE_CHOICES = [
        (TYPE_REFILL, 'Refill'),
        (TYPE_EXCHANGE, 'Exchange'),
    ]

    SCHEDULE_ASAP = 'asap'
    SCHEDULE_LATER = 'later'
    SCHEDULE_CHOICES = [
        (SCHEDULE_ASAP, 'As soon as possible'),
        (SCHEDULE_LATER, 'Later'),
    ]

    PAY_MOMO = 'momo'
    PAY_AIRTEL = 'airtel'
    PAY_CASH = 'cash'
    PAY_CHOICES = [
        (PAY_MOMO, 'MTN MoMo'),
        (PAY_AIRTEL, 'Airtel Money'),
        (PAY_CASH, 'Cash on delivery'),
    ]

    PAY_PENDING = 'pending'
    PAY_PAID = 'paid'
    PAY_STATUS_CHOICES = [
        (PAY_PENDING, 'Pending'),
        (PAY_PAID, 'Paid'),
    ]

    STATUS_NEW = 'new'
    STATUS_ACCEPTED = 'accepted'
    STATUS_RIDER_ASSIGNED = 'rider_assigned'
    STATUS_COLLECTED = 'collected'
    STATUS_ON_THE_WAY = 'on_the_way'
    STATUS_DELIVERED = 'delivered'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_RIDER_ASSIGNED, 'Rider assigned'),
        (STATUS_COLLECTED, 'Collected'),
        (STATUS_ON_THE_WAY, 'On the way'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    code = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='orders')
    rider = models.ForeignKey(
        Rider, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name='orders')
    order_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_REFILL)
    delivery_address = models.CharField(max_length=255)
    address_note = models.CharField(max_length=255, blank=True, default='')
    lat = models.FloatField(default=0.3285)
    lng = models.FloatField(default=32.5590)
    schedule = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default=SCHEDULE_ASAP)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAY_CHOICES, default=PAY_MOMO)
    payment_status = models.CharField(max_length=20, choices=PAY_STATUS_CHOICES, default=PAY_PENDING)
    gas_price = models.PositiveIntegerField()
    delivery_fee = models.PositiveIntegerField(default=5000)
    total = models.PositiveIntegerField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_NEW)
    rider_fee = models.PositiveIntegerField(default=4000)
    handover_confirmed = models.BooleanField(default=False)
    empty_collected = models.BooleanField(default=False)
    seal_checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rider_assigned_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    on_the_way_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def mark_status(self, status):
        self.status = status
        now = timezone.now()
        mapping = {
            self.STATUS_ACCEPTED: 'accepted_at',
            self.STATUS_RIDER_ASSIGNED: 'rider_assigned_at',
            self.STATUS_COLLECTED: 'collected_at',
            self.STATUS_ON_THE_WAY: 'on_the_way_at',
            self.STATUS_DELIVERED: 'delivered_at',
            self.STATUS_REJECTED: 'rejected_at',
            self.STATUS_CANCELLED: 'cancelled_at',
        }
        field = mapping.get(status)
        if field:
            setattr(self, field, now)
        self.save()


class Rating(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='rating')
    rider_stars = models.PositiveSmallIntegerField(default=5)
    vendor_stars = models.PositiveSmallIntegerField(default=5)
    tags = models.JSONField(default=list, blank=True)
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Rating for {self.order.code}'


class Settlement(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='settlements')
    week_start = models.DateField()
    gas_sales = models.PositiveIntegerField()
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    payout = models.PositiveIntegerField()

    class Meta:
        ordering = ['-week_start']
        unique_together = ('vendor', 'week_start')

    def __str__(self):
        return f'{self.vendor.name} week of {self.week_start}'

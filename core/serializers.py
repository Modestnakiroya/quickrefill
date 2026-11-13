from rest_framework import serializers

from .models import Order, Rating, Rider, Settlement, StockItem, User, Vendor


def format_ugx(amount):
    return f'UGX {int(amount):,}'.replace(',', ',')


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role']


class StockItemSerializer(serializers.ModelSerializer):
    price_display = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)

    class Meta:
        model = StockItem
        fields = [
            'id', 'brand', 'size_kg', 'price_refill', 'price_exchange',
            'quantity', 'low_stock_threshold', 'price_display', 'availability',
            'distance_km', 'vendor_name', 'vendor',
        ]

    def get_price_display(self, obj):
        order_type = self.context.get('order_type', 'refill')
        price = obj.price_exchange if order_type == 'exchange' else obj.price_refill
        return format_ugx(price)

    def get_availability(self, obj):
        if obj.quantity <= 0:
            return 'out_of_stock'
        if obj.is_low:
            return 'low'
        return 'in_stock'

    def get_distance_km(self, obj):
        distances = self.context.get('distances', {})
        key = f'{obj.brand}-{obj.size_kg}'
        return distances.get(key, 1.2)


class OrderSerializer(serializers.ModelSerializer):
    stock_item_detail = StockItemSerializer(source='stock_item', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    rider_name = serializers.SerializerMethodField()
    gas_price_display = serializers.SerializerMethodField()
    delivery_fee_display = serializers.SerializerMethodField()
    total_display = serializers.SerializerMethodField()
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    item_label = serializers.SerializerMethodField()
    rated = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'code', 'customer', 'vendor', 'vendor_name', 'rider', 'rider_name',
            'stock_item', 'stock_item_detail', 'order_type', 'delivery_address',
            'address_note', 'lat', 'lng', 'schedule', 'scheduled_time',
            'payment_method', 'payment_status', 'gas_price', 'delivery_fee', 'total',
            'gas_price_display', 'delivery_fee_display', 'total_display',
            'status', 'status_label', 'rider_fee', 'handover_confirmed',
            'empty_collected', 'seal_checked', 'created_at', 'accepted_at',
            'rider_assigned_at', 'collected_at', 'on_the_way_at', 'delivered_at',
            'item_label', 'rated',
        ]
        read_only_fields = [
            'code', 'customer', 'vendor', 'rider', 'gas_price', 'delivery_fee',
            'total', 'status', 'rider_fee', 'payment_status',
        ]

    def get_rider_name(self, obj):
        if obj.rider:
            return obj.rider.user.get_full_name() or obj.rider.user.username
        return None

    def get_gas_price_display(self, obj):
        return format_ugx(obj.gas_price)

    def get_delivery_fee_display(self, obj):
        return format_ugx(obj.delivery_fee)

    def get_total_display(self, obj):
        return format_ugx(obj.total)

    def get_item_label(self, obj):
        return f'{obj.stock_item.brand} {obj.stock_item.size_kg} kg {obj.get_order_type_display()}'

    def get_rated(self, obj):
        return hasattr(obj, 'rating')


class OrderCreateSerializer(serializers.Serializer):
    stock_item_id = serializers.IntegerField()
    order_type = serializers.ChoiceField(choices=Order.TYPE_CHOICES)
    delivery_address = serializers.CharField(max_length=255)
    address_note = serializers.CharField(max_length=255, required=False, allow_blank=True)
    lat = serializers.FloatField(required=False, default=0.3285)
    lng = serializers.FloatField(required=False, default=32.5590)
    schedule = serializers.ChoiceField(choices=Order.SCHEDULE_CHOICES, default=Order.SCHEDULE_ASAP)
    scheduled_time = serializers.DateTimeField(required=False, allow_null=True)
    payment_method = serializers.ChoiceField(choices=Order.PAY_CHOICES)
    mark_paid = serializers.BooleanField(required=False, default=False)


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'order', 'rider_stars', 'vendor_stars', 'tags', 'comment', 'created_at']
        read_only_fields = ['order']


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'location', 'verified', 'accepting_orders',
            'rating', 'lat', 'lng',
        ]


class RiderSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = Rider
        fields = [
            'id', 'name', 'phone', 'online', 'rating', 'trips_count',
            'vehicle_plate', 'lat', 'lng',
        ]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class SettlementSerializer(serializers.ModelSerializer):
    gas_sales_display = serializers.SerializerMethodField()
    payout_display = serializers.SerializerMethodField()
    commission_amount = serializers.SerializerMethodField()
    commission_amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Settlement
        fields = [
            'id', 'vendor', 'week_start', 'gas_sales', 'gas_sales_display',
            'commission_percent', 'commission_amount', 'commission_amount_display',
            'payout', 'payout_display',
        ]

    def get_gas_sales_display(self, obj):
        return format_ugx(obj.gas_sales)

    def get_payout_display(self, obj):
        return format_ugx(obj.payout)

    def get_commission_amount(self, obj):
        return int(obj.gas_sales * float(obj.commission_percent) / 100)

    def get_commission_amount_display(self, obj):
        return format_ugx(self.get_commission_amount(obj))

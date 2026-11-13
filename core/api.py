import random
import urllib.request
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Order, Rating, Rider, Settlement, StockItem, User, Vendor
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    RatingSerializer,
    SettlementSerializer,
    StockItemSerializer,
    UserSerializer,
    VendorSerializer,
    format_ugx,
)

STOCK_DISTANCES = {
    'Stabex-6': 1.2,
    'Stabex-12': 1.2,
    'Stabex-45': 1.2,
    'Oryx-12': 2.0,
    'Oryx-6': 2.0,
    'Total-6': 2.8,
    'Total-12': 2.8,
    'Shell-6': 2.0,
    'Shell-12': 2.8,
    'Hashi-6': 1.2,
    'Hashi-45': 2.0,
}

# Approximate coordinates for common Kampala places & landmarks when customer only enters place name
KAMPALA_PLACES = {
    'kikoni': (0.3332, 32.5588),
    'garden courts': (0.3335, 32.5582),
    'makerere': (0.3326, 32.5686),
    'wandegeya': (0.3350, 32.5670),
    'nakulabye': (0.3264, 32.5553),
    'kasubi': (0.3285, 32.5520),
    'mulago': (0.3422, 32.5768),
    'kamwokya': (0.3415, 32.5869),
    'kololo': (0.3315, 32.5935),
    'ntinda': (0.3542, 32.6122),
    'bukoto': (0.3510, 32.5975),
    'naguru': (0.3425, 32.6058),
    'bugolobi': (0.3175, 32.6175),
    'mengo': (0.3075, 32.5585),
    'rubaga': (0.3038, 32.5522),
    'ndeeba': (0.2965, 32.5592),
    'kabalagala': (0.2968, 32.6012),
    'kansanga': (0.2882, 32.6075),
    'muyenga': (0.2925, 32.6185),
    'kawempe': (0.3672, 32.5615),
    'bwaise': (0.3538, 32.5625),
    'kalerwe': (0.3555, 32.5735),
    'kyebando': (0.3578, 32.5842),
    'banda': (0.3485, 32.6285),
    'kyambogo': (0.3498, 32.6318),
    'kireka': (0.3475, 32.6492),
    'naalya': (0.3685, 32.6412),
    'namugongo': (0.3825, 32.6562),
    'nakasero': (0.3215, 32.5795),
    'kampala': (0.3163, 32.5822),
}


def _resolve_place_coords(place_name, landmark='', lat=None, lng=None):
    """Resolve approximate coordinates from a place name/landmark if exact coords were not supplied."""
    if lat is not None and lng is not None:
        try:
            f_lat, f_lng = float(lat), float(lng)
            if not (abs(f_lat - 0.3285) < 1e-6 and abs(f_lng - 32.5590) < 1e-6):
                return f_lat, f_lng
        except (TypeError, ValueError):
            pass

    text = f'{place_name or ""} {landmark or ""}'.lower()
    for keyword, coords in KAMPALA_PLACES.items():
        if keyword in text:
            return coords
    return (0.3285, 32.5590)


def _full_phone(nine):
    return f'+256{nine}'


HARDCODED_RIDER_PHONE = '+256700000002'
HELP_DESK_PHONE = '0784113900'


def _generate_order_code():
    while True:
        code = f'QR-{random.randint(20000, 99999)}'
        if not Order.objects.filter(code=code).exists():
            return code


def _get_seeded_rider():
    user = User.objects.filter(phone=_full_phone('700000002'), role=User.ROLE_RIDER).first()
    if not user:
        return None
    return getattr(user, 'rider_profile', None)


def _require_role(user, role):
    return user.is_authenticated and user.role == role


def map_tile(request, z, x, y):
    """Serve OpenStreetMap tiles with local disk cache so no API key is ever required."""
    cache_dir = Path(settings.BASE_DIR) / '.tile_cache' / str(z) / str(x)
    cache_file = cache_dir / f'{y}.png'
    if cache_file.exists():
        return HttpResponse(
            cache_file.read_bytes(),
            content_type='image/png',
            headers={'Cache-Control': 'public, max-age=86400'},
        )
    url = f'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'QuickRefill-Kampala-MVP/1.0 (+https://quickrefill.ug)',
            'Accept': 'image/png,image/*;q=0.8',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(data)
        return HttpResponse(
            data,
            content_type='image/png',
            headers={'Cache-Control': 'public, max-age=86400'},
        )
    except Exception:
        return HttpResponse(status=502)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_account(request):
    email = str(request.data.get('email', '')).strip().lower()
    password = str(request.data.get('password', ''))
    role = str(request.data.get('role', '')).strip()
    if role not in (User.ROLE_CUSTOMER, User.ROLE_RIDER, User.ROLE_VENDOR):
        return Response({'detail': 'Select a valid account role.'}, status=400)
    user_record = User.objects.filter(email__iexact=email).first()
    if user_record is None and role != User.ROLE_CUSTOMER:
        role_name = 'rider' if role == User.ROLE_RIDER else 'vendor'
        return Response({
            'detail': f'This email is not registered as a {role_name}. Contact QuickRefill support.'
        }, status=403)
    username = user_record.username if user_record else email
    user = authenticate(request, username=username, password=password)
    if user is None and password != password.strip():
        user = authenticate(request, username=username, password=password.strip())
    if user is None:
        return Response({'detail': 'Email or password is incorrect.'}, status=401)
    if user.role != role:
        return Response({
            'detail': f'This account is registered as a {user.role}, not a {role}.'
        }, status=403)
    login(request, user)
    destination = {
        User.ROLE_CUSTOMER: '/app/',
        User.ROLE_RIDER: '/rider/',
        User.ROLE_VENDOR: '/vendor/',
    }.get(user.role, '/app/')
    return Response({'ok': True, 'user': UserSerializer(user).data, 'redirect': destination})


@api_view(['POST'])
@permission_classes([AllowAny])
def register_customer(request):
    email = str(request.data.get('email', '')).strip().lower()
    password = str(request.data.get('password', ''))
    password_confirm = str(request.data.get('password_confirm', ''))
    first_name = str(request.data.get('first_name', '')).strip()
    last_name = str(request.data.get('last_name', '')).strip()
    phone = str(request.data.get('phone', '')).strip() or None
    if not first_name:
        return Response({'detail': 'Enter your first name.'}, status=400)
    try:
        User._meta.get_field('email').clean(email, None)
    except ValidationError:
        return Response({'detail': 'Enter a valid email address.'}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return Response({'detail': 'An account with this email already exists. Sign in instead.'}, status=409)
    if phone and User.objects.filter(phone=phone).exists():
        return Response({'detail': 'An account with this phone number already exists.'}, status=409)
    if password != password_confirm:
        return Response({'detail': 'The passwords do not match.'}, status=400)

    user = User(
        username=f'qr_{uuid.uuid4().hex}',
        email=email,
        phone=phone[:20] if phone else None,
        first_name=first_name[:150],
        last_name=last_name[:150],
        role=User.ROLE_CUSTOMER,
    )
    try:
        validate_password(password, user)
    except ValidationError as error:
        return Response({'detail': ' '.join(error.messages)}, status=400)
    user.set_password(password)
    try:
        with transaction.atomic():
            user.save()
    except IntegrityError:
        return Response({
            'detail': 'An account with this email already exists. Sign in instead.'
        }, status=409)
    login(request, user)
    return Response({
        'ok': True,
        'user': UserSerializer(user).data,
        'redirect': '/app/',
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    data = UserSerializer(request.user).data
    if request.user.role == User.ROLE_VENDOR and hasattr(request.user, 'vendor_profile'):
        data['vendor'] = VendorSerializer(request.user.vendor_profile).data
    if request.user.role == User.ROLE_RIDER and hasattr(request.user, 'rider_profile'):
        rider = request.user.rider_profile
        data['rider'] = {
            'online': rider.online,
            'rating': float(rider.rating),
            'trips_count': rider.trips_count,
            'vehicle_plate': rider.vehicle_plate,
        }
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def stock_list(request):
    size = request.query_params.get('size')
    order_type = request.query_params.get('type', 'refill')
    qs = StockItem.objects.select_related('vendor').all()
    if size:
        qs = qs.filter(size_kg=int(size))
    # Do not list empty 45kg stock.
    qs = qs.exclude(size_kg=45, quantity=0)
    serializer = StockItemSerializer(
        qs,
        many=True,
        context={'order_type': order_type, 'distances': STOCK_DISTANCES},
    )
    items = []
    for item, obj in zip(serializer.data, qs):
        price = obj.price_exchange if order_type == 'exchange' else obj.price_refill
        item['price'] = price
        item['price_display'] = format_ugx(price)
        item['continue_total'] = price + settings.DELIVERY_FEE
        item['continue_total_display'] = format_ugx(price + settings.DELIVERY_FEE)
        if not obj.vendor.accepting_orders:
            item['availability'] = 'out_of_stock'
            item['availability_label'] = 'Vendor currently paused'
            item['clickable'] = False
        elif obj.quantity <= 0:
            item['availability_label'] = 'Out of stock'
            item['clickable'] = False
        elif obj.is_low:
            item['availability_label'] = f'Only {obj.quantity} left'
            item['clickable'] = True
        else:
            item['availability_label'] = f'In stock - {item["distance_km"]} km'
            item['clickable'] = True
        items.append(item)
    return Response(items)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def orders_collection(request):
    if request.method == 'GET':
        qs = Order.objects.filter(customer=request.user).select_related(
            'stock_item', 'vendor', 'rider__user'
        )
        return Response(OrderSerializer(qs, many=True).data)

    ser = OrderCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data
    try:
        stock = StockItem.objects.select_related('vendor').get(id=data['stock_item_id'])
    except StockItem.DoesNotExist:
        return Response({'detail': 'Stock item not found.'}, status=404)
    if stock.quantity <= 0:
        return Response({'detail': 'This item is out of stock.'}, status=400)
    if not stock.vendor.accepting_orders:
        return Response({'detail': 'Vendor is not accepting orders right now.'}, status=400)

    price = stock.price_exchange if data['order_type'] == Order.TYPE_EXCHANGE else stock.price_refill
    delivery_fee = settings.DELIVERY_FEE
    payment_status = Order.PAY_PAID if data.get('mark_paid') else Order.PAY_PENDING
    if data['payment_method'] == Order.PAY_CASH:
        payment_status = Order.PAY_PENDING

    resolved_lat, resolved_lng = _resolve_place_coords(
        data['delivery_address'],
        data.get('address_note', ''),
        data.get('lat'),
        data.get('lng'),
    )

    order = Order.objects.create(
        code=_generate_order_code(),
        customer=request.user,
        vendor=stock.vendor,
        stock_item=stock,
        order_type=data['order_type'],
        delivery_address=data['delivery_address'],
        address_note=data.get('address_note', ''),
        lat=resolved_lat,
        lng=resolved_lng,
        schedule=data.get('schedule', Order.SCHEDULE_ASAP),
        scheduled_time=data.get('scheduled_time'),
        payment_method=data['payment_method'],
        payment_status=payment_status,
        gas_price=price,
        delivery_fee=delivery_fee,
        total=price + delivery_fee,
        rider_fee=settings.RIDER_FEE,
        status=Order.STATUS_NEW,
    )
    return Response(OrderSerializer(order).data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    try:
        order = Order.objects.select_related(
            'stock_item', 'vendor', 'rider__user', 'customer'
        ).get(id=order_id)
    except Order.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
    if request.user.role == User.ROLE_CUSTOMER and order.customer_id != request.user.id:
        return Response({'detail': 'Forbidden.'}, status=403)
    if request.user.role == User.ROLE_VENDOR:
        if not hasattr(request.user, 'vendor_profile') or order.vendor_id != request.user.vendor_profile.id:
            return Response({'detail': 'Forbidden.'}, status=403)
    if request.user.role == User.ROLE_RIDER:
        rider = getattr(request.user, 'rider_profile', None)
        if not rider or (order.rider_id and order.rider_id != rider.id):
            if order.status not in (Order.STATUS_RIDER_ASSIGNED, Order.STATUS_ACCEPTED) and order.rider_id != getattr(rider, 'id', None):
                pass
    return Response(OrderSerializer(order).data)


def _interpolate(v_lat, v_lng, c_lat, c_lng, progress):
    progress = max(0.0, min(1.0, progress))
    return (
        v_lat + (c_lat - v_lat) * progress,
        v_lng + (c_lng - v_lng) * progress,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_track(request, order_id):
    try:
        order = Order.objects.select_related(
            'stock_item', 'vendor', 'rider__user', 'customer'
        ).get(id=order_id)
    except Order.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    vendor = order.vendor
    rider = order.rider
    eta_minutes = 45
    rider_lat = None
    rider_lng = None
    rider_name = None
    rider_rating = None
    rider_trips = None
    rider_plate = None
    rider_phone = HARDCODED_RIDER_PHONE

    if rider:
        rider_name = rider.user.get_full_name() or rider.user.username
        rider_rating = float(rider.rating)
        rider_trips = rider.trips_count
        rider_plate = rider.vehicle_plate
        rider_lat = rider.lat
        rider_lng = rider.lng
        if rider.user.phone:
            rider_phone = rider.user.phone

    status_progress = {
        Order.STATUS_NEW: 1,
        Order.STATUS_ACCEPTED: 1,
        Order.STATUS_RIDER_ASSIGNED: 2,
        Order.STATUS_COLLECTED: 3,
        Order.STATUS_ON_THE_WAY: 3,
        Order.STATUS_DELIVERED: 4,
        Order.STATUS_REJECTED: 0,
        Order.STATUS_CANCELLED: 0,
    }

    start_move_at = order.on_the_way_at or order.collected_at
    if order.status in (Order.STATUS_COLLECTED, Order.STATUS_ON_THE_WAY) and start_move_at:
        elapsed = (timezone.now() - start_move_at).total_seconds()
        trip_seconds = 180  # 3 minute simulated trip
        progress = min(1.0, elapsed / trip_seconds)
        rider_lat, rider_lng = _interpolate(
            vendor.lat, vendor.lng, order.lat, order.lng, progress
        )
        if rider:
            rider.lat = rider_lat
            rider.lng = rider_lng
            rider.save(update_fields=['lat', 'lng'])
        eta_minutes = max(1, int(round((1 - progress) * 15)))
    elif order.status == Order.STATUS_DELIVERED:
        eta_minutes = 0
        rider_lat, rider_lng = order.lat, order.lng
    elif order.status in (Order.STATUS_RIDER_ASSIGNED, Order.STATUS_ACCEPTED):
        eta_minutes = 35
    elif order.status == Order.STATUS_NEW:
        eta_minutes = 50

    return Response({
        'order_id': order.id,
        'code': order.code,
        'status': order.status,
        'status_label': order.get_status_display(),
        'progress_step': status_progress.get(order.status, 0),
        'item_label': f'{order.stock_item.brand} {order.stock_item.size_kg} kg',
        'order_type': order.order_type,
        'payment_method': order.payment_method,
        'payment_status': order.payment_status,
        'seal_checked': order.seal_checked,
        'eta_minutes': eta_minutes,
        'rider_name': rider_name,
        'rider_rating': rider_rating,
        'rider_trips': rider_trips,
        'rider_plate': rider_plate,
        'rider_phone': rider_phone,
        'help_phone': HELP_DESK_PHONE,
        'rider_lat': rider_lat,
        'rider_lng': rider_lng,
        'vendor_lat': vendor.lat,
        'vendor_lng': vendor.lng,
        'vendor_name': vendor.name,
        'vendor_location': vendor.location,
        'customer_lat': order.lat,
        'customer_lng': order.lng,
        'delivery_address': order.delivery_address,
        'address_note': order.address_note,
        'delivered_at': order.delivered_at,
        'created_at': order.created_at,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_rate(request, order_id):
    try:
        order = Order.objects.get(id=order_id, customer=request.user)
    except Order.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
    if order.status != Order.STATUS_DELIVERED:
        return Response({'detail': 'Order not delivered yet.'}, status=400)
    if hasattr(order, 'rating'):
        return Response({'detail': 'Already rated.'}, status=400)
    rating = Rating.objects.create(
        order=order,
        rider_stars=int(request.data.get('rider_stars', 5)),
        vendor_stars=int(request.data.get('vendor_stars', 5)),
        tags=request.data.get('tags', []),
        comment=request.data.get('comment', ''),
    )
    return Response(RatingSerializer(rating).data, status=201)


# ---- Vendor ----

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_orders(request):
    if not _require_role(request.user, User.ROLE_VENDOR):
        return Response({'detail': 'Vendors only.'}, status=403)
    vendor = request.user.vendor_profile
    qs = Order.objects.filter(vendor=vendor).select_related(
        'stock_item', 'customer', 'rider__user'
    )
    return Response(OrderSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vendor_accept(request, order_id):
    if not _require_role(request.user, User.ROLE_VENDOR):
        return Response({'detail': 'Vendors only.'}, status=403)
    vendor = request.user.vendor_profile
    try:
        order = Order.objects.select_related('stock_item').get(id=order_id, vendor=vendor)
    except Order.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
    if order.status != Order.STATUS_NEW:
        return Response({'detail': 'Order cannot be accepted.'}, status=400)
    if order.stock_item.quantity <= 0:
        return Response({'detail': 'Out of stock.'}, status=400)

    order.stock_item.quantity -= 1
    order.stock_item.save(update_fields=['quantity'])

    rider = _get_seeded_rider()
    order.status = Order.STATUS_ACCEPTED
    order.accepted_at = timezone.now()
    if rider:
        order.rider = rider
        order.status = Order.STATUS_RIDER_ASSIGNED
        order.rider_assigned_at = timezone.now()
    order.save()
    return Response(OrderSerializer(order).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vendor_reject(request, order_id):
    if not _require_role(request.user, User.ROLE_VENDOR):
        return Response({'detail': 'Vendors only.'}, status=403)
    vendor = request.user.vendor_profile
    try:
        order = Order.objects.get(id=order_id, vendor=vendor)
    except Order.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
    if order.status != Order.STATUS_NEW:
        return Response({'detail': 'Order cannot be rejected.'}, status=400)
    order.mark_status(Order.STATUS_REJECTED)
    return Response(OrderSerializer(order).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_stats(request):
    if not _require_role(request.user, User.ROLE_VENDOR):
        return Response({'detail': 'Vendors only.'}, status=403)
    vendor = request.user.vendor_profile
    today = timezone.localdate()
    orders = Order.objects.filter(vendor=vendor)
    return Response({
        'orders_today': orders.filter(created_at__date=today).exclude(
            status__in=[Order.STATUS_REJECTED, Order.STATUS_CANCELLED]
        ).count(),
        'waiting': orders.filter(status=Order.STATUS_NEW).count(),
        'out_for_delivery': orders.filter(
            status__in=[
                Order.STATUS_RIDER_ASSIGNED,
                Order.STATUS_COLLECTED,
                Order.STATUS_ON_THE_WAY,
            ]
        ).count(),
        'rating': float(vendor.rating),
        'accepting_orders': vendor.accepting_orders,
        'verified': vendor.verified,
        'name': vendor.name,
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def vendor_stock(request):
    if not _require_role(request.user, User.ROLE_VENDOR):
        return Response({'detail': 'Vendors only.'}, status=403)
    vendor = request.user.vendor_profile
    if request.method == 'GET':
        qs = StockItem.objects.filter(vendor=vendor).order_by('size_kg', 'brand')
        data = []
        for item in qs:
            data.append({
                'id': item.id,
                'brand': item.brand,
                'size_kg': item.size_kg,
                'price_refill': item.price_refill,
                'price_exchange': item.price_exchange,
                'quantity': item.quantity,
                'is_low': item.is_low,
                'price_display': format_ugx(item.price_refill),
                'price_exchange_display': format_ugx(item.price_exchange),
            })
        return Response(data)

    item_id = request.data.get('id')
    try:
        item = StockItem.objects.get(id=item_id, vendor=vendor)
    except StockItem.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
    if 'quantity' in request.data:
        item.quantity = max(0, int(request.data['quantity']))
    if 'price_refill' in request.data:
        item.price_refill = int(request.data['price_refill'])
    if 'price_exchange' in request.data:
        item.price_exchange = int(request.data['price_exchange'])
    item.save()
    return Response({
        'id': item.id,
        'brand': item.brand,
        'size_kg': item.size_kg,
        'quantity': item.quantity,
        'price_refill': item.price_refill,
        'price_exchange': item.price_exchange,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def vendor_accepting(request):
    if not _require_role(request.user, User.ROLE_VENDOR):
        return Response({'detail': 'Vendors only.'}, status=403)
    vendor = request.user.vendor_profile
    vendor.accepting_orders = bool(request.data.get('accepting_orders', vendor.accepting_orders))
    vendor.save(update_fields=['accepting_orders'])
    return Response({'accepting_orders': vendor.accepting_orders})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_settlement(request):
    if not _require_role(request.user, User.ROLE_VENDOR):
        return Response({'detail': 'Vendors only.'}, status=403)
    vendor = request.user.vendor_profile
    qs = Settlement.objects.filter(vendor=vendor)
    return Response(SettlementSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_ratings(request):
    if not _require_role(request.user, User.ROLE_VENDOR):
        return Response({'detail': 'Vendors only.'}, status=403)
    vendor = request.user.vendor_profile
    ratings = Rating.objects.filter(order__vendor=vendor).select_related('order').order_by('-created_at')
    data = []
    for r in ratings:
        data.append({
            'order_code': r.order.code,
            'rider_stars': r.rider_stars,
            'vendor_stars': r.vendor_stars,
            'tags': r.tags,
            'comment': r.comment,
            'created_at': r.created_at,
        })
    return Response(data)


# ---- Rider ----

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rider_online(request):
    if not _require_role(request.user, User.ROLE_RIDER):
        return Response({'detail': 'Riders only.'}, status=403)
    rider = request.user.rider_profile
    rider.online = bool(request.data.get('online', True))
    rider.save(update_fields=['online'])
    return Response({'online': rider.online})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rider_jobs_available(request):
    if not _require_role(request.user, User.ROLE_RIDER):
        return Response({'detail': 'Riders only.'}, status=403)
    rider = request.user.rider_profile

    session_active = request.session.get('rider_active_order')
    if session_active:
        try:
            active_order = Order.objects.select_related(
                'stock_item', 'vendor', 'customer'
            ).get(id=session_active, rider=rider)
            if active_order.status not in (
                Order.STATUS_DELIVERED, Order.STATUS_REJECTED, Order.STATUS_CANCELLED
            ):
                return Response({'mode': 'active', 'job': _job_payload(active_order, request)})
        except Order.DoesNotExist:
            pass

    in_progress = Order.objects.filter(
        rider=rider,
        status__in=[Order.STATUS_COLLECTED, Order.STATUS_ON_THE_WAY],
    ).select_related('stock_item', 'vendor', 'customer').order_by('-created_at').first()
    if in_progress:
        return Response({'mode': 'active', 'job': _job_payload(in_progress, request)})

    if not rider.online:
        return Response({'mode': 'offline', 'job': None})

    declined = set(request.session.get('declined_jobs', []))
    offer = Order.objects.filter(
        rider=rider,
        status=Order.STATUS_RIDER_ASSIGNED,
    ).select_related('stock_item', 'vendor', 'customer').exclude(
        id__in=declined
    ).order_by('-created_at').first()
    if offer:
        return Response({'mode': 'offer', 'job': _job_payload(offer, request)})

    return Response({'mode': 'idle', 'job': None})


def _job_payload(order, request=None):
    payment_confirmed = bool(request.session.get(f'payment_step_{order.id}')) if request is not None else False
    collected_done = order.collected_at is not None or order.status in (
        Order.STATUS_COLLECTED, Order.STATUS_ON_THE_WAY, Order.STATUS_DELIVERED
    )
    steps_done = {
        'collected': collected_done,
        'seal_checked': order.seal_checked,
        'handover': order.handover_confirmed,
        'empty_collected': order.empty_collected,
        'payment': payment_confirmed or (
            order.payment_method == Order.PAY_CASH and order.payment_status == Order.PAY_PAID
        ),
        'delivered': order.status == Order.STATUS_DELIVERED,
    }

    step_order = ['collected', 'seal_checked', 'handover', 'empty_collected', 'payment', 'delivered']
    current_step = 1
    for i, key in enumerate(step_order, start=1):
        if not steps_done.get(key):
            current_step = i
            break
        current_step = i + 1
    if steps_done['delivered']:
        current_step = 6

    rider = order.rider
    rider_lat = rider.lat if rider else 0.3380
    rider_lng = rider.lng if rider else 32.5640

    return {
        'id': order.id,
        'code': order.code,
        'stage': 'dropoff' if collected_done else 'pickup',
        'fee': order.rider_fee,
        'fee_display': format_ugx(order.rider_fee),
        'distance_km': 3.2,
        'eta_min': 18,
        'vendor_name': order.vendor.name,
        'vendor_location': order.vendor.location,
        'pickup': order.vendor.name + ' · ' + order.vendor.location,
        'dropoff': order.delivery_address,
        'address_note': order.address_note,
        'cylinder': f'{order.stock_item.brand} {order.stock_item.size_kg} kg',
        'order_type': order.order_type,
        'payment_method': order.payment_method,
        'payment_status': order.payment_status,
        'payment_label': (
            'MoMo paid' if order.payment_method == Order.PAY_MOMO and order.payment_status == Order.PAY_PAID
            else 'Airtel paid' if order.payment_method == Order.PAY_AIRTEL and order.payment_status == Order.PAY_PAID
            else 'Cash on delivery'
        ),
        'status': order.status,
        'steps_done': steps_done,
        'current_step': min(current_step, 5),
        'customer_phone': order.customer.phone or '+256700000001',
        'help_phone': HELP_DESK_PHONE,
        'lat': order.lat,
        'lng': order.lng,
        'vendor_lat': order.vendor.lat,
        'vendor_lng': order.vendor.lng,
        'rider_lat': rider_lat,
        'rider_lng': rider_lng,
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rider_accept_job(request, order_id):
    if not _require_role(request.user, User.ROLE_RIDER):
        return Response({'detail': 'Riders only.'}, status=403)
    rider = request.user.rider_profile
    try:
        order = Order.objects.select_related('stock_item', 'vendor', 'customer').get(
            id=order_id, rider=rider, status=Order.STATUS_RIDER_ASSIGNED
        )
    except Order.DoesNotExist:
        return Response({'detail': 'Job not found.'}, status=404)
    request.session['rider_active_order'] = order.id
    declined = request.session.get('declined_jobs', [])
    if order.id in declined:
        declined = [i for i in declined if i != order.id]
        request.session['declined_jobs'] = declined
    return Response({'mode': 'active', 'job': _job_payload(order, request)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rider_decline_job(request, order_id):
    if not _require_role(request.user, User.ROLE_RIDER):
        return Response({'detail': 'Riders only.'}, status=403)
    rider = request.user.rider_profile
    try:
        order = Order.objects.get(id=order_id, rider=rider, status=Order.STATUS_RIDER_ASSIGNED)
    except Order.DoesNotExist:
        return Response({'detail': 'Job not found.'}, status=404)
    declined = request.session.get('declined_jobs', [])
    if order.id not in declined:
        declined.append(order.id)
    request.session['declined_jobs'] = declined
    if request.session.get('rider_active_order') == order.id:
        del request.session['rider_active_order']
    return Response({'ok': True, 'detail': 'Declined.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rider_step(request, order_id):
    if not _require_role(request.user, User.ROLE_RIDER):
        return Response({'detail': 'Riders only.'}, status=403)
    rider = request.user.rider_profile
    try:
        order = Order.objects.select_related('stock_item', 'vendor', 'customer').get(
            id=order_id, rider=rider
        )
    except Order.DoesNotExist:
        return Response({'detail': 'Job not found.'}, status=404)

    step = request.data.get('step')
    steps_sequence = [
        'collected', 'seal_checked', 'handover', 'empty_collected', 'payment', 'delivered'
    ]
    if step not in steps_sequence:
        return Response({'detail': 'Invalid step.'}, status=400)

    done = {
        'collected': bool(order.collected_at) or order.status in (
            Order.STATUS_COLLECTED, Order.STATUS_ON_THE_WAY, Order.STATUS_DELIVERED
        ),
        'seal_checked': order.seal_checked,
        'handover': order.handover_confirmed,
        'empty_collected': order.empty_collected,
        'payment': False,
        'delivered': order.status == Order.STATUS_DELIVERED,
    }

    idx = steps_sequence.index(step)
    for prev in steps_sequence[:idx]:
        if prev == 'payment':
            continue
        if prev == 'collected' and not done['collected']:
            return Response({'detail': f'Complete {prev} first.'}, status=400)
        if prev == 'seal_checked' and not order.seal_checked:
            return Response({'detail': f'Complete {prev} first.'}, status=400)
        if prev == 'handover' and not order.handover_confirmed:
            return Response({'detail': f'Complete {prev} first.'}, status=400)
        if prev == 'empty_collected' and not order.empty_collected:
            return Response({'detail': f'Complete {prev} first.'}, status=400)

    if step == 'collected':
        order.status = Order.STATUS_COLLECTED
        order.collected_at = timezone.now()
        order.save()
        rider.lat = order.vendor.lat
        rider.lng = order.vendor.lng
        rider.save(update_fields=['lat', 'lng'])
    elif step == 'seal_checked':
        order.seal_checked = True
        order.status = Order.STATUS_ON_THE_WAY
        order.on_the_way_at = timezone.now()
        order.save()
    elif step == 'handover':
        order.handover_confirmed = True
        if order.status != Order.STATUS_ON_THE_WAY:
            order.status = Order.STATUS_ON_THE_WAY
            order.on_the_way_at = order.on_the_way_at or timezone.now()
        order.save()
    elif step == 'empty_collected':
        order.empty_collected = True
        order.save(update_fields=['empty_collected'])
    elif step == 'payment':
        if order.payment_method == Order.PAY_CASH:
            order.payment_status = Order.PAY_PAID
            order.save(update_fields=['payment_status'])
        request.session[f'payment_step_{order.id}'] = True
    elif step == 'delivered':
        if not (order.collected_at and order.seal_checked and order.handover_confirmed and order.empty_collected):
            return Response({'detail': 'Complete all checklist steps first.'}, status=400)
        if order.payment_method == Order.PAY_CASH and order.payment_status != Order.PAY_PAID:
            return Response({'detail': 'Collect payment first.'}, status=400)
        if order.payment_method in (Order.PAY_MOMO, Order.PAY_AIRTEL) and not request.session.get(f'payment_step_{order.id}'):
            request.session[f'payment_step_{order.id}'] = True
        order.status = Order.STATUS_DELIVERED
        order.delivered_at = timezone.now()
        order.save()
        rider.trips_count += 1
        rider.lat = order.lat
        rider.lng = order.lng
        rider.save(update_fields=['trips_count', 'lat', 'lng'])
        if request.session.get('rider_active_order') == order.id:
            del request.session['rider_active_order']

    order.refresh_from_db()
    return Response({'mode': 'active', 'job': _job_payload(order, request)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rider_summary(request):
    if not _require_role(request.user, User.ROLE_RIDER):
        return Response({'detail': 'Riders only.'}, status=403)
    rider = request.user.rider_profile
    today = timezone.localdate()
    delivered_today = Order.objects.filter(
        rider=rider, status=Order.STATUS_DELIVERED, delivered_at__date=today
    )
    trips_today = delivered_today.count()
    earnings_today = trips_today * settings.RIDER_FEE
    return Response({
        'name': rider.user.get_full_name() or rider.user.first_name,
        'online': rider.online,
        'rating': float(rider.rating),
        'trips_count': rider.trips_count,
        'vehicle_plate': rider.vehicle_plate,
        'trips_today': trips_today,
        'earnings_today': earnings_today,
        'earnings_today_display': format_ugx(earnings_today),
        'phone': rider.user.phone,
    })
